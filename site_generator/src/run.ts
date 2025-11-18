import { validateAllScrapers, validateNewScrapers } from "./parseScrapers";

async function main() {
  // check if in CI and NOT workflow_dispatch
  if (process.env.CI && process.env.GITHUB_EVENT_NAME !== "workflow_dispatch") {
    await validateNewScrapers();
  } else await validateAllScrapers();
}
main();
