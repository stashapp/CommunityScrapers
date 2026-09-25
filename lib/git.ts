export interface Commit {
  /** Abbreviated hash */
  version: string;
  /** UTC, as `YYYY-MM-DD HH:MM:SS` */
  date: string;
}

export async function lastCommit(path: string): Promise<Commit> {
  const { success, stdout, stderr } = await new Deno.Command("git", {
    args: [
      "log",
      "-n",
      "1",
      "--date=format-local:%F %T",
      "--pretty=format:%h|%ad",
      "--",
      path,
    ],
    env: { TZ: "UTC0" },
  }).output();
  const decoder = new TextDecoder();
  if (!success) {
    throw new Error(`git log ${path}: ${decoder.decode(stderr)}`);
  }
  const [version, date] = decoder.decode(stdout).trim().split("|");
  if (!version || !date) {
    throw new Error(`${path} has no commits`);
  }
  return { version, date };
}
