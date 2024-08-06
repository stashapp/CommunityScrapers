import { simpleGit, SimpleGitOptions } from "simple-git";

const options: Partial<SimpleGitOptions> = {
  baseDir: `.`,
};
export const git = simpleGit(options);
