export function getBadgeForCompleted(count) {
  if (count >= 250) return { label: "Kıdemli Etiketleyici", level: 4 };
  if (count >= 100) return { label: "Uzman Etiketleyici", level: 3 };
  if (count >= 50) return { label: "Deneyimli Etiketleyici", level: 2 };
  if (count >= 10) return { label: "Başlangıç Etiketleyici", level: 1 };
  return { label: "Yeni Etiketleyici", level: 0 };
}

