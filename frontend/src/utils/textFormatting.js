export function formatDocumentTextForReading(text) {
  if (!text) return "";

  const lines = String(text)
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .replace(/\u00a0/g, " ")
    .split("\n")
    .map((line) => line.replace(/[ \t\f\v]+/g, " ").trim());

  const paragraphs = [];
  let current = "";
  let previousWasBlank = false;

  const flushCurrent = () => {
    if (!current) return;
    paragraphs.push(cleanInlineSpacing(current));
    current = "";
  };

  for (const line of lines) {
    if (!line) {
      flushCurrent();
      if (!previousWasBlank && paragraphs.length) paragraphs.push("");
      previousWasBlank = true;
      continue;
    }

    previousWasBlank = false;

    if (startsStructuralLine(line)) {
      flushCurrent();
      current = line;
      continue;
    }

    if (!current) {
      current = line;
      continue;
    }

    if (shouldPreserveLineBreak(current, line)) {
      flushCurrent();
      current = line;
    } else {
      current = `${current} ${line}`;
    }
  }

  flushCurrent();

  return paragraphs
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function startsStructuralLine(line) {
  return (
    /^[-*\u2022]\s+/.test(line) ||
    /^\d+\.\s+/.test(line) ||
    /^\d+\)\s+(?=\p{Lu})/u.test(line) ||
    /^\p{L}\)\s+/u.test(line) ||
    /^[IVXLCDM]+[.)]\s+/i.test(line)
  );
}

function shouldPreserveLineBreak(previous, next) {
  if (startsStructuralLine(next)) return true;
  if (isHeadingLike(previous) || isHeadingLike(next)) return true;
  if (!/[.!?;:]\s*$/.test(previous)) return false;
  if (!/^[\p{Lu}0-9]/u.test(next)) return false;
  if (/[:;]\s*$/.test(previous) && looksLikeSameSentenceContinuation(next)) {
    return false;
  }
  return true;
}

/** İki nokta / noktalı virgül sonrası satır sonu; VKN, miktar veya cümle devamı ise parçalama. */
function looksLikeSameSentenceContinuation(next) {
  const t = next.trim();
  if (!t) return false;
  if (/^\d{3}\s+\d{3}\s+\d{4}\b/.test(t)) return true;
  if (/^\p{Ll}/u.test(t)) return true;
  if (/^\(\d+\)\s/.test(t)) return true;
  if (/^\d{4}\s+sayılı/u.test(t)) return true;
  return false;
}

function isHeadingLike(line) {
  const withoutNumbers = line.replace(/[0-9()[\].,\-/\s]/g, "");
  if (withoutNumbers.length < 4) return false;
  return line.endsWith(":") && withoutNumbers === withoutNumbers.toLocaleUpperCase("tr-TR");
}

function cleanInlineSpacing(text) {
  return text
    .replace(/"\s*([^"\n]*?)\s*"/g, '"$1"')
    .replace(/\u201c\s*/g, "\u201c")
    .replace(/\s*\u201d/g, "\u201d")
    .replace(/\s+([,.;:!?])/g, "$1")
    .replace(/([([{])\s+/g, "$1")
    .replace(/\s+([)\]}])/g, "$1")
    .replace(/[ \t\f\v]{2,}/g, " ")
    .trim();
}
