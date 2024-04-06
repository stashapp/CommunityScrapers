#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const safeRequire = (name) => {
  try {
    return require(name);
  } catch (error) {
    if (error && error.code === 'MODULE_NOT_FOUND') {
      console.log(`Error: Cannot find module '${name}', have you installed the dependencies?`);
      process.exit(1);
    }
    throw error;
  }
};

const Ajv = safeRequire('ajv');
const betterAjvErrors = safeRequire('better-ajv-errors');
const chalk = safeRequire('chalk');
const YAML = safeRequire('yaml');

// https://www.peterbe.com/plog/nodejs-fs-walk-or-glob-or-fast-glob
function walk(directory, ext, filepaths = []) {
  const files = fs.readdirSync(directory);
  for (const filename of files) {
    const filepath = path.join(directory, filename);
    if (fs.statSync(filepath).isDirectory()) {
      walk(filepath, ext, filepaths);
    } else if (path.extname(filename) === ext) {
      filepaths.push(filepath);
    }
  }
  return filepaths;
}

// https://stackoverflow.com/a/53833620
const isSorted = arr => arr.every((v,i,a) => !i || a[i-1] <= v);

class Validator {
  constructor(flags) {
    this.allowDeprecations = flags.includes('-d');
    this.stopOnError = !flags.includes('-a');
    this.sortedURLs = flags.includes('-s');
    this.verbose = flags.includes('-v');

    const schemaPath = path.resolve(__dirname, './scraper.schema.json');
    this.schema = JSON.parse(fs.readFileSync(schemaPath, 'utf8'));
    this.ajv = new Ajv({
      // allErrors: true,
      jsonPointers: true,
      extendRefs: true, // should be 'fail' with ajv v7
      strictKeywords: true,
    });

    this.mappingPattern = /^([a-z]+)By(Fragment|Name|URL)$/;

    if (!!this.ajv.getKeyword('deprecated')) {
      this.ajv.removeKeyword('deprecated');
    }

    this.ajv.addKeyword('deprecated', {
      validate: function v(schema, data, parentSchema, dataPath, parentData, parentPropertyName) {
        if (schema) {
          v.errors = [{
            keyword: 'deprecated',
            message: (
              parentSchema.description
                ? parentSchema.description.replace('[DEPRECATED] ', '')
                : `\`${parentPropertyName}\` is deprecated`
            ),
            params: { keyword: 'deprecated' },
            dataPath,
          }];
        }
        return !schema;
      },
      valid: (this.allowDeprecations ? true : undefined),
    });
  }

  run(files) {
    let scrapers;

    if (files && Array.isArray(files) && files.length > 0) {
      scrapers = files.map(file => path.resolve(file));
    } else {
      const scrapersDir = path.resolve(__dirname, '../scrapers');
      scrapers = walk(scrapersDir, '.yml');
    }

    const yamlLoadOptions = {
      prettyErrors: true,
      version: '1.2',
      merge: true,
    };

    let result = true;
    const validate = this.ajv.compile(this.schema);

    for (const file of scrapers) {
      const relPath = path.relative(process.cwd(), file);
      let contents, data;
      try {
        contents = fs.readFileSync(file, 'utf8');
        data = YAML.parse(contents, yamlLoadOptions);
      } catch (error) {
        console.error(`${chalk.red(chalk.bold('ERROR'))} in: ${relPath}:`);
        error.stack = null;
        console.error(error);
        result = result && false;
        if (this.stopOnError) break;
        else continue;
      }

      let valid = validate(data);

      // If schema validation did not pass, don't try to validate mappings.
      if (valid) {
        const mappingErrors = this.getMappingErrors(data);
        const validMapping = mappingErrors.length === 0;
        if (!validMapping) {
          validate.errors = (validate.errors || []).concat(mappingErrors);
        }

        valid = valid && validMapping;
      }

      // Output validation errors
      if (!valid) {
        const output = betterAjvErrors('scraper', data, validate.errors, { indent: 2 });
        console.log(output);
      }

      if (this.verbose || !valid) {
        const validColor = valid ? chalk.green : chalk.red;
        console.log(`${relPath} Valid: ${validColor(valid)}`);
      }

      result = result && valid;

      if (!valid && this.stopOnError) break;
    }

    if (!this.verbose && result) {
      console.log(chalk.green('Validation passed!'));
    }

    return result;
  }

  getMappingErrors(data) {
    return [].concat(
      this._collectConfigMappingErrors(data),
      this._collectScraperDefinitionErrors(data),
      this._collectCookieErrors(data),
    );
  }

  _collectConfigMappingErrors(data) {
    const errors = [];

    if (data.sceneByName && !data.sceneByQueryFragment) {
      errors.push({
        keyword: 'sceneByName',
        message: `a \`sceneByQueryFragment\` configuration is required for \`sceneByName\` to work`,
        params: { keyword: 'sceneByName' },
        dataPath: '/sceneByName',
      });
    }

    return errors;
  }

  _collectScraperDefinitionErrors(data) {
    const hasStashServer = Object.keys(data).includes('stashServer');
    const xPathScrapers = data.xPathScrapers ? Object.keys(data.xPathScrapers) : [];
    const jsonScrapers = data.jsonScrapers ? Object.keys(data.jsonScrapers) : [];

    let needsStashServer = false;
    const configuredXPathScrapers = [];
    const configuredJsonScrapers = [];

    const errors = [];

    Object.entries(data).forEach(([key, value]) => {
      const match = this.mappingPattern.exec(key);
      if (!match) {
        return;
      }

      const seenURLs = {};

      const type = match[1];

      const multiple = value instanceof Array;
      (multiple ? value : [value]).forEach(({ action, scraper, url }, idx) => {
        const dataPath = `/${key}${multiple ? `/${idx}` : ''}`;

        if (action === 'stash') {
          needsStashServer = true;
          if (!hasStashServer) {
            errors.push({
              keyword: 'action',
              message: `root object should contain a \`stashServer\` definition`,
              params: { keyword: 'action' },
              dataPath: dataPath + '/action',
            });
          }
          return;
        }

        if (action === 'scrapeXPath') {
          configuredXPathScrapers.push(scraper);
          if (!xPathScrapers.includes(scraper)) {
            errors.push({
              keyword: 'scraper',
              message: `xPathScrapers should contain a XPath scraper definition for \`${scraper}\``,
              params: { keyword: 'scraper' },
              dataPath: dataPath + '/scraper',
            });
          } else if (!data.xPathScrapers || !data.xPathScrapers[scraper][type]) {
            errors.push({
              keyword: scraper,
              message: `\`${scraper}\` should create an object of type \`${type}\``,
              params: { keyword: scraper },
              dataPath: `/xPathScrapers/${scraper}`,
            });
          }

          if (url) {
            url.forEach((u, uIdx) => {
              const exists = seenURLs[u];
              if (exists) {
                errors.push({
                  keyword: 'url',
                  message: `URLs for type \`${type}\` should be unique, already exists on ${exists}`,
                  params: { keyword: 'url' },
                  dataPath: `${dataPath}/url/${uIdx}`,
                });
              } else {
                seenURLs[u] = `${dataPath}/url/${uIdx}`;
              }
            });

            if (this.sortedURLs && !isSorted(url)) {
              errors.push({
                keyword: 'url',
                message: 'URL list should be sorted in ascending alphabetical order',
                params: { keyword: 'url' },
                dataPath: dataPath + '/url',
              });
            }
          }

          return;
        }

        if (action === 'scrapeJson') {
          configuredJsonScrapers.push(scraper);
          if (!jsonScrapers.includes(scraper)) {
            errors.push({
              keyword: 'scraper',
              message: `jsonScrapers should contain a JSON scraper definition for \`${scraper}\``,
              params: { keyword: 'scraper' },
              dataPath: dataPath + '/scraper',
            });
          } else if (!data.jsonScrapers || !data.jsonScrapers[scraper][type]) {
            errors.push({
              keyword: scraper,
              message: `\`${scraper}\` should create an object of type \`${type}\``,
              params: { keyword: scraper },
              dataPath: `/jsonScrapers/${scraper}`,
            });
          }

          if (url) {
            url.forEach((u, uIdx) => {
              const exists = seenURLs[u];
              if (exists) {
                errors.push({
                  keyword: 'url',
                  message: `URLs for type \`${type}\` should be unique, already exists on ${exists}`,
                  params: { keyword: 'url' },
                  dataPath: `${dataPath}/url/${uIdx}`,
                });
              } else {
                seenURLs[u] = `${dataPath}/url/${uIdx}`;
              }
            });

            if (this.sortedURLs && !isSorted(url)) {
              errors.push({
                keyword: 'url',
                message: 'URL list should be sorted in ascending alphabetical order',
                params: { keyword: 'url' },
                dataPath: dataPath + '/url',
              });
            }
          }

          return;
        }

        // if (action === 'script') {
        //   return;
        // }
        //
        // errors.push({
        //   keyword: 'action',
        //   message: `unsupported action \`${action}\``,
        //   params: { keyword: 'action' },
        //   dataPath: dataPath + '/action',
        // });
      });
    });

    // Check for unused definitions

    if (!needsStashServer && hasStashServer) {
      errors.unshift({
        keyword: 'stashServer',
        message: '`stashServer` is defined, but never used',
        params: { keyword: 'stashServer' },
        dataPath: '/stashServer',
      });
    }

    return errors;
  }

  _collectCookieErrors(data) {
    const errors = [];

    const cookies = data.driver && data.driver.cookies;
    if (cookies) {
      const usesCDP = Boolean(data.driver && data.driver.useCDP);
      cookies.forEach((cookieItem, idx) => {
        const hasCookieURL = 'CookieURL' in cookieItem;
        if (!usesCDP && !hasCookieURL) {
          errors.push({
            keyword: 'CookieURL',
            message: '`CookieURL` is required because useCDP is `false`',
            params: { keyword: 'CookieURL' },
            dataPath: `/driver/cookies/${idx}`,
          });
        } else if (usesCDP && hasCookieURL) {
          errors.push({
            keyword: 'CookieURL',
            message: 'Should not have `CookieURL` because useCDP is `true`',
            params: { keyword: 'CookieURL' },
            dataPath: `/driver/cookies/${idx}/CookieURL`,
          });
        }
      });
    }

    return errors;
  }
}

function main(flags, files) {
  const args = process.argv.slice(2)
  flags = (flags === undefined) ? args.filter(arg => arg.startsWith('-')) : flags;
  files = (files === undefined) ? args.filter(arg => !arg.startsWith('-')) : files;
  const validator = new Validator(flags);
  const result = validator.run(files);
  if (flags.includes('--ci')) {
    process.exit(result ? 0 : 1);
  }
}

if (require.main === module) {
  main();
}

module.exports = main;
module.exports.Validator = Validator;
