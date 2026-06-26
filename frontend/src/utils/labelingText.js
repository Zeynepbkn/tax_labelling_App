export function cleanLabelingFieldText(value) {
  return String(value || "")
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .split("\n")
    .map((line) => line.replace(/^\s*[-\u2013\u2014]\s*/, "").trimEnd())
    .join("\n")
    .trim();
}
