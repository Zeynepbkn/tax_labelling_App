export function hasAtLeastOneQuestion(questions) {
  return Array.isArray(questions) && questions.some((q) => (q || "").trim().length > 0);
}

export function isNonEmptyText(value) {
  return (value || "").trim().length > 0;
}

const nameSeparators = new Set(["-", "'", "."]);

export function normalizeFullName(value) {
  return (value || "").trim().split(/\s+/).filter(Boolean).join(" ");
}

export function isValidPersonFullName(value) {
  const parts = normalizeFullName(value).split(" ").filter(Boolean);
  if (parts.length < 2) return false;

  return parts.every((part) => {
    const chars = Array.from(part);
    const letters = chars.filter((char) => /\p{L}/u.test(char));
    return (
      letters.length >= 2 &&
      chars.every((char) => /\p{L}/u.test(char) || nameSeparators.has(char))
    );
  });
}

