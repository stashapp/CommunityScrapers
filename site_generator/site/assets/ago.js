// s-ago https://github.com/sebastiansandqvist/s-ago
// LICENCE MIT by Sebastian Sandqvist

function formatDate(diff, divisor, unit, past) {
  var val = Math.round(Math.abs(diff) / divisor);
  return val <= 1 ? past : `${val} ${unit}s ago`;
}
var units = [
  { max: 518400000, value: 86400000, name: "day", past: "yesterday" },
  { max: 2419200000, value: 604800000, name: "week", past: "last week" },
  { max: 28512000000, value: 2592000000, name: "month", past: "last month" }, // max: 11 months
];
export default function ago(date, max) {
  var diff = Date.now() - date.getTime();
  for (const unit of units) {
    if (Math.abs(diff) < unit.max || (max && unit.name === max)) {
      return formatDate(diff, unit.value, unit.name, unit.past);
    }
  }
  return formatDate(diff, 31536000000, "year", "last year");
}
