#!/bin/bash

# builds a repository of scrapers
# outputs to _site with the following structure:
# index.yml
# <scraper_id>.zip
# Each zip file contains the scraper.yml file and any other files in the same directory

outdir="$1"
if [ -z "$outdir" ]; then
    outdir="_site"
fi

rm -rf "$outdir"
mkdir -p "$outdir"

buildScraper() 
{
    f=$1
    # get the scraper id from the filename
    scraper_id=$(basename "$f" .yml)

    echo "Processing $scraper_id"

    # create a directory for the version
    version=$(git log -n 1 --pretty=format:%h -- "$f")
    updated=$(git log -n 1 --date="format:%F %T %z" --pretty=format:%ad -- "$f")
    
    # create the zip file
    # copy other files
    zipfile=$(realpath "$outdir/$scraper_id.zip")
    
    pushd $(dirname "$f") > /dev/null
    if [ $(dirname "$f") != "./scrapers" ]; then
        zip -r "$zipfile" . > /dev/null
    else
        zip "$zipfile" "$scraper_id.yml" > /dev/null
    fi
    popd > /dev/null

    name=$(grep "^name:" "$f" | cut -d' ' -f2- | sed -e 's/\r//' -e 's/^"\(.*\)"$/\1/')

    # write to spec index
    echo "- id: $scraper_id
  name: $name
  version: $version
  date: $updated
  path: $scraper_id.zip
  sha256: $(sha256sum "$zipfile" | cut -d' ' -f1)
" >> "$outdir"/index.yml
}

# find all yml files in ./scrapers - these are packages individually
for f in ./scrapers/*.yml; do 
    buildScraper "$f"
done

for f in ./scrapers/*/*.yml; do 
    buildScraper "$f"
done