export const PASSING_SCORE = 75;

export const CONTEXT_GUIDE_ITEMS = [
  'Bağlam, mükellefin soru kipinden önce anlattığı olay, faaliyet, işlem, belge, dönem, taraflar, tutar ve vergi türü gibi açıklama kısmıdır.',
  'Soru kutusuna yalnızca son soru ifadesini yazmayın; mükellefin soruyu sormak için açıkladığı bilgilendirme bölümünü de olduğu gibi soruya dahil edin.',
  'Aynı belgede birden fazla soru varsa ortak olay/bağlam kısmını her soru kutusunda tekrar edin.',
  'Sorunun anlamı kısa bir kökle bitiyorsa yine bağlamı koruyun; örneğin "uygulanacak KDV oranı" ifadesini bağlamıyla birlikte "uygulanacak KDV oranı nedir" diye tamamlayın.',
  {
    important: true,
    text: '"Olup olmayacağı", "değerlendirilip değerlendirilmeyeceği" veya "nasıl değerlendirileceği" gibi zaten soru anlamı taşıyan ifadeleri olduğu gibi bırakın; sonlarına "nedir" soru kipini eklemeyin.',
  },
];

export const QUESTION_EXTRACTION_ITEMS = [
  'Soruları bulmak için özelge metninin başından mükellef talebinin bittiği yere kadar olan bölüme özellikle dikkat edin.',
  'Talep bitişleri ham metinde çoğunlukla şu kalıplarla görünür: "sorulmaktadır.", "talep edildiği anlaşılmaktadır.", "talep edildiği anlaşılmıştır.", "talep ettiğiniz anlaşılmıştır.", "talep edilmektedir.", "görüşü istenilmektedir.", "talep ettiğiniz anlaşılmaktadır." "sorulmuştur.".',
  'Aynı belgede birden fazla talep varsa her talebi ayrı soru kutusuna yazın.',
  'Çoklu talepte "ve" veya "ile" tek başına tek soru demek değildir; virgülle ayrılmış ikinci olay özeti veya aynı cümlede iki vergi rejimi ayrı soru gerektirebilir.',
  'Sorularınızı bağlamıyla yazın; pratikte çoğu soru en az 100-150 karakter civarında olmalıdır.',
  {
    important: true,
    text: '"Olup olmayacağı", "uygulanıp uygulanmayacağı", "değerlendirilip değerlendirilmeyeceği" ve "nasıl değerlendirileceği" gibi ifadeler zaten soru anlamı taşır. Bu şekilde biten soruları değiştirmeyin ve sonlarına "nedir" eklemeyin.',
  },
  'Soru kısmına kopyaladığınız metinde satır başında "-" madde işareti varsa silin.',
];

export const ANSWER_EXTRACTION_ITEMS = [
  'Cevap alanı genellikle talep bitişlerinden hemen sonra başlar.',
  'İdarenin açıklama ve değerlendirme kısmını "Cevap" alanına alın.',
  'Cevap kısmını genellikle "Bilgi edinilmesini rica ederim" veya "Bilgi edinilmesini arz ederim" kapanışına kadar alın.',
  'Kapanış cümlesini cevaba dahil etmeyin.',
  'Cevabı yapıştırırken kelimeler arasında oluşan gereksiz çift veya çoklu boşlukları tek boşluğa indirin.',
];

export const QUICK_GUIDE_SECTIONS = [
  {
    title: 'Bağlam Nedir?',
    accent: 'context',
    items: CONTEXT_GUIDE_ITEMS,
  },
  {
    title: 'Soruları Ayıklama',
    accent: 'question',
    items: QUESTION_EXTRACTION_ITEMS,
  },
  {
    title: 'Cevabı Ayırt Etme',
    accent: 'answer',
    items: ANSWER_EXTRACTION_ITEMS,
  },
];
