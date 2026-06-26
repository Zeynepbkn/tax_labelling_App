from __future__ import annotations

from sqlalchemy import case, select
from sqlalchemy.orm import Session, joinedload

from app.db.models.document import Document, DocumentSplit
from app.db.models.training import TrainingLabel
from app.services.text_normalization_service import normalize_document_whitespace


TRAINING_EXAMPLE_LABEL_IDS: list[int] = [433, 437, 410, 411, 414, 402, 387, 338, 418, 419]

TRAINING_EXAMPLE_NOTES: dict[int, str] = {
    433: (
        "Çoklu soruyu tespit etme (evrak 1rigt0gq2j1iq3): Özelge metninin başından talep bölümünün bittiği "
        "`konularında bilgi istenildiği anlaşılmaktadır.` ifadesine kadar okuyun. Ortak giriş "
        "(`İlgide kayıtlı özelge talep formu ve eklerinin incelenmesinden, ... çerçevesinde;`) tüm talepler için "
        "geçerlidir; ardından virgül ve noktalı virgülle ayrılmış iki ayrı olay özeti gelir. İlk blokta "
        "Haydar Aliyev Deniz Terminali (BIL İskelesi) ham petrol yüklemesi için barınma ve ulaşım hizmeti gelirinin "
        "KV ve KDV istisnası; ikinci blokta BOTAŞ protokolü kapsamında P.İ.M. hizmetleri nedeniyle aktarılan gelirin "
        "KV ve KDV istisnası sorulur. Her blok içinde `ve` hem kurumlar vergisini hem KDV’yi bağlar; bu yüzden yalnızca "
        "`ve` gördüğünüzde otomatik tek soru varsaymayın. İkinci soruyu ayıran ipucu, birinci talebin "
        "`... istisna olup olmadığının,` ile bitmesi ve hemen ardından yeni bir cümleyle (`Şubeniz ile BOTAŞ...`) "
        "ikinci olayın anlatılmasıdır. Gold kayıtta her soru için anlaşma bağlamı baştan tekrarlanır; yalnızca "
        "hizmet senaryosu ve talep özeti değişir."
    ),
    437: (
        "Çoklu soruyu tespit etme (evrak 1ok5mbsih715yc): Talep tek paragraf gibi görünse de "
        "`... kazancın kurumlar vergisi ve katma değer vergisi istisnasından yararlanıp yararlanamayacağınız hususunda ... "
        "talep edilmektedir.` cümlesinde `kurumlar vergisi ve katma değer vergisi` iki ayrı hukuki soru oluşturur; "
        "KV istisnası ile KDV istisnası ayrı soru kutularına yazılır. `ile` bağlacı (internet sitesi aracılığı ile...) "
        "bağlamı birleştirir; `ve` ise burada iki vergi türünü yan yana getirir. Teknokent/Ar-Ge ve Emlak Muayene Raporu "
        "bağlamı her iki gold soruda da aynen korunur, yalnızca son talep cümlesi vergi türüne göre ayrılır."
    ),
    338: (
        "Bu örnek 'nedir' ekinin özellikle önemli olduğu farklı bir kalıptır. Talep kısmında ifade "
        "`3065 sayılı Katma Değer Vergisi (KDV) ve 5520 sayılı Kurumlar Vergisi Kanunları karşısındaki durumu hususunda "
        "Defterdarlığımız görüşü talep edilmektedir` şeklindedir. Bu ifade doğrudan soru kipiyle bitmediği için soru, "
        "`3065 sayılı Katma Değer Vergisi (KDV) ve 5520 sayılı Kurumlar Vergisi Kanunları karşısındaki durumu nedir` "
        "şeklinde tamamlanır. `hususunda görüş talep edilmektedir` kısmı soruya eklenmez; anlamı soru yapmak için genellikle "
        "`nedir` eki kullanılır."
    ),
    402: (
        "Bu örnekte aynı belge içinde birden fazla talep vardır. Her soru ayrı yazılır ve Eurobondların edinim/itfa "
        "bağlamı her bir soruya tekrar eklenir; sadece ikinci talep cümlesi tek başına bırakılmaz."
    ),
    387: (
        "Bu örnekte talep kısmı `bahşişlerin vergilendirilmesi hususunda görüş talep edilmektedir` diye biter. "
        "Metinde açık bir soru kipi olmadığı için soru, bağlam korunarak `bahşişlerin vergilendirilmesi nedir` şeklinde "
        "tamamlanır. Bu tür `... vergilendirilmesi hususunda görüş talep edilmektedir` kalıplarında genellikle `nedir` "
        "soru eki eklenir."
    ),
    410: (
        "Bu örnekte üç ayrı soru vardır. Yurtiçinden ihraç kayıtlı mermer alınması, yurtdışındaki komisyon firması "
        "ve komisyon faturasının yansıtılması bağlamı her soru için tekrar yazılır; ardından ilgili alt talep eklenir."
    ),
    411: (
        "Bu örnekte aynı olaydan doğan birden fazla talep ayrı soru yapılır. Teknik aksaklık/ayıp nedeniyle yapılan "
        "işlemlere ilişkin ortak bağlam her soru için korunur ve her soru kendi özel talebiyle tamamlanır."
    ),
    418: (
        "Bu örnekte aynı özelge içindeki üç ayrı talep ayrı soru olarak çıkarılır: potansiyel vergi numarası, "
        "POS cihazı kullanımı ve fiş/fatura düzenleme. Ortak bağlam, her sorunun başına tekrar eklenir; "
        "sadece kısa madde metni tek başına bırakılmaz."
    ),
    419: (
        "Bu örnekte bazı talep ifadeleri metinde doğrudan soru köküyle bitmez. Böyle durumlarda bağlam korunur "
        "ve ifade soru haline getirilir. Özellikle 'uygulanacak KDV oranı' gibi köksüz kalan yapılarda "
        "'uygulanacak KDV oranı nedir' şeklinde 'nedir' soru eki mutlaka eklenir. Talep kısmında örneğin "
        "`KDV oranı %18 olan kağıtların KDV oranı %8 olan tela ile lamine yaparak satılmasında uygulanacak KDV oranı` "
        "ifadesi yer alır; soru halinde `uygulanacak KDV oranı nedir` diye tamamlanır."
    ),
}


def get_training_examples(db: Session, limit: int = 5) -> list[dict]:
    label_ids = TRAINING_EXAMPLE_LABEL_IDS[:limit]
    order_by_label_id = case(
        {label_id: index for index, label_id in enumerate(label_ids)},
        value=TrainingLabel.id,
    )
    fixed_stmt = (
        select(Document)
        .join(TrainingLabel, TrainingLabel.document_id == Document.id)
        .where(TrainingLabel.id.in_(label_ids))
        .options(joinedload(Document.training_label).joinedload(TrainingLabel.questions))
        .order_by(order_by_label_id)
    )
    ordered_fixed = db.execute(fixed_stmt).unique().scalars().all()

    remaining = max(0, limit - len(ordered_fixed))
    extra_docs: list[Document] = []
    if remaining > 0:
        stmt = (
            select(Document)
            .where(Document.split == DocumentSplit.training)
            .join(TrainingLabel, TrainingLabel.document_id == Document.id)
            .where(TrainingLabel.id.not_in(label_ids))
            .options(joinedload(Document.training_label).joinedload(TrainingLabel.questions))
            .order_by(Document.order_index.asc(), Document.id.asc())
            .limit(remaining)
        )
        extra_docs = db.execute(stmt).unique().scalars().all()

    docs = ordered_fixed + extra_docs
    out: list[dict] = []
    for d in docs:
        tl = d.training_label
        out.append(
            {
                "training_label_id": tl.id if tl else None,
                "evrak_id": d.evrak_id,
                "ozelge_metni": normalize_document_whitespace(d.display_text),
                "gold_sorular": [q.gold_question_text for q in (tl.questions if tl else [])],
                "gold_cevap": tl.gold_cevap if tl else None,
                "aciklama": _join_notes(tl.aciklama if tl else None, TRAINING_EXAMPLE_NOTES.get(tl.id if tl else 0)),
            }
        )
    return out


def get_training_guide(exam_passed: bool) -> dict:
    if exam_passed:
        return {
            "title": "Kısa Bilgilendirme",
            "content_markdown": (
                "Sınavı geçtiniz. Artık gerçek etiketleme havuzundan belge alabilirsiniz.\n\n"
                "- Sorularınızı **bağlamıyla** yazın (en az 100-150 karakter tahmini olarak).\n"
                "- Bağlam; mükellefin soru kipinden önce anlattığı olay, faaliyet, işlem, taraflar, belge, dönem, tutar ve vergi türü gibi açıklama kısmıdır. Bu bilgilendirme bölümünü soru kutusuna olduğu gibi dahil edin.\n"
                "- Aynı belgede birden fazla soru varsa her talebi ayrı soru kutusuna yazın; ortak olay/bağlam kısmını her soru için tekrar ekleyin.\n"
                "- Çoklu talepte `ve` / `ile` tek başına tek soru demek değildir; virgülle ayrılmış ikinci olay özeti veya aynı cümlede iki vergi rejimi ayrı soru gerektirebilir.\n"
                "- Soruları bulmak için özelge metninin başından talep bitişine kadar olan bölüme özellikle dikkat edin; sorular genellikle bu bölümü kapsar.\n"
                "- Talep bitişleri ham metinde çoğunlukla şu kalıplarla görünür: `sorulmaktadır.`, `sorulmuştur`, `talep edildiği anlaşılmaktadır.`, `talep edildiği anlaşılmıştır.`, `talep ettiğiniz anlaşılmıştır.`, `talep edilmektedir.`, `görüşü istenilmektedir. `, `talep ettiğiniz anlaşılmaktadır. `.\n"
                "- Cevap alanı genellikle bu talep bitişlerinden hemen sonra başlar.\n"
                "- Cevap kısmını genellikle `Bilgi edinilmesini rica ederim` veya `Bilgi edinilmesini arz ederim` kapanışına kadar, Bilgi edinilmesini rica ederim kapanış cümlesi dahil olmayacak şekilde alın.\n"
                "- Cevabı kopyalayıp yapıştırırken kelimeler arasında oluşan gereksiz çift/çoklu boşlukları tek boşluğa indirin.\n"
                "- Soru kısmına kopyaladığınız metinde satır başında `-` madde işareti varsa silin.\n"
                "- Metinde soru kipi yoksa ifadeyi soru haline getirin; `uygulanacak KDV oranı`, `vergilendirilmesi` veya `Kanunları karşısındaki durumu` gibi kalıplar genellikle `nedir` ekiyle tamamlanır.\n"
            ),
        }
    return {
        "title": "Eğitim / Kullanım Kılavuzu",
        "content_markdown": (
            "Amaç: Özelge metninden mükellefin sorularını bağlamıyla çıkarın ve idarenin değerlendirme/cevap kısmını ayrı alana yapıştırın.\n\n"
            "## Bağlam ne demektir?\n"
            "Bağlam, mükellefin soru kipinden önce anlattığı açıklama bölümüdür: olayın ne olduğu, hangi faaliyet veya işlemden bahsedildiği, taraflar, belge türü, dönem, tutar, vergi türü ve soruyu etkileyen diğer bilgiler bu kapsamdadır. "
            "Soru kutusuna yalnızca `KDV oranı nedir?` gibi kısa bir ifade yazılmamalıdır; mükellefin bu soruyu sormak için açıkladığı bilgilendirme kısmı da olduğu gibi soruya dahil edilmelidir. "
            "Birden fazla soru varsa ortak bağlam her soru kutusunda tekrar edilmelidir.\n\n"
            "## Sorular nerede aranır?\n"
            "Soruları bulmak için özelge metninin başından talep bitişine kadar olan bölüme özellikle dikkat edin. "
            "Sorular genellikle bu bitiş ifadelerine kadar olan kısmı kapsar; bu yüzden sadece son soru cümlesini değil, o soruyu etkileyen bağlamı da alın.\n"
            "Aynı belgede birden fazla soru veya talep varsa, her talep ayrı soru kutusuna yazılır. Ortak olay/bağlam kısmı yalnızca ilk soruda bırakılmaz; her soru için tekrar eklenir. "
            "Örneğin aynı belge içindeki ayrı talepler, ortak bağlam korunarak ayrı ayrı hazırlanmalıdır.\n\n"
            "## Tek belgede birden fazla soruyu nasıl ayırt edersiniz?\n"
            "Özelge metninin başından mükellef talebinin bittiği yere kadar (çoğunlukla `... talep edilmektedir.`, "
            "`... sorulmaktadır.`, `... anlaşılmaktadır.` gibi talep kapanışlarına kadar) okuyun. Çoklu soru için "
            "birkaç tipik işaret vardır: (1) Aynı girişten sonra virgül veya noktalı virgülle ayrılmış birden fazla "
            "tam talep özeti; (2) `konularında` gibi çoğul ifadelerle kapanan talepler; (3) Tek cümlede `kurumlar vergisi "
            "ve katma değer vergisi` gibi yan yana iki vergi rejimi. `ve`, `ile`, `veya` gibi bağlaçlar tek başına "
            "tek soru anlamına gelmez: bağlaç cümleyi birleştirebilir veya iki vergi konusunu yan yana getirebilir. ve bağlacı iki ayrı vergi talepleriyse bunları ayrı sorular şeklinde yazmalısınız.\n\n"
            "**Training label 433** (evrak `1rigt0gq2j1iq3`): Talep bölümünde ortak anlaşma girişinden sonra iki ayrı "
            "operasyonel senaryo (BIL İskelesi hizmetleri / BOTAŞ protokolü ve P.İ.M. hizmetleri) üst üste anlatılır; "
            "her biri KV ve KDV istisnası içerdiği için gold kayıtta iki ayrı soru oluşturulmuştur. Eğitim kartındaki "
            "metin özetinde talep kapanışına kadar olan kısım, altında ise bu evraktan türetilmiş doğru sorular listelenir.\n\n"
            "**Training label 437** (evrak `1ok5mbsih715yc`): Talep tek paragraf olsa da `kurumlar vergisi ve katma değer vergisi "
            "istisnasından` ifadesi iki ayrı istisna sorusunu ifade eder; gold kayıtta Teknokent/Ar-Ge bağlamı her iki "
            "soruda tekrarlanır, son cümle KV veya KDV istisnasına göre ayrılır.\n"
            "Bu talep bitişleri ham metinde çoğunlukla şu şekilde görünebilir: `sorulmaktadır.`, `talep edildiği anlaşılmaktadır.`, `talep edildiği anlaşılmıştır.`, `talep ettiğiniz anlaşılmıştır.`, `talep edilmektedir. `, `görüşü istenilmektedir. `, `talep ettiğiniz anlaşılmaktadır.`.\n\n"
            "## Cevap alanı nasıl alınır?\n"
            "Cevap alanı genellikle mükellefin talebini bitiren bu kalıplardan hemen sonra başlar: `sorulmaktadır.`, `talep edildiği anlaşılmaktadır.`, `talep edildiği anlaşılmıştır.`, `talep ettiğiniz anlaşılmıştır.`, `talep edilmektedir.`, `    görüşü istenilmektedir.`, `talep ettiğiniz anlaşılmaktadır.`.\n"
            "Bu cümleden sonraki idare değerlendirmesi **Cevap** alanına yapıştırılır ve genellikle `Bilgi edinilmesini rica ederim` veya `Bilgi edinilmesini arz ederim` kapanış cümlesine kadar, kapanış cümlesi dahil olmayacak şekilde alınır.\n"
            "Cevabı kopyalayıp yapıştırırken kelimeler arasında oluşan gereksiz çift/çoklu boşluklar temizlenmeli ve tek boşluk bırakılmalıdır.\n"
            "\n\n## Madde işaretleri nasıl temizlenir?\n"
            "Soruyu veya cevabı içeren kısım `-Şirketinizle...`, `-Leasing şirketi...` gibi satır başı tireleriyle gelirse, bu `-` işaretlerini silerek kaydedin. "
            "Metin `Şirketinizle...` ve `Leasing şirketi...` şeklinde başlamalıdır.\n"
            "\n\n## Soru kökü yoksa ne yapılır?\n"
            "Bazı özelgelerde talep maddesi açık bir soru kipiyle bitmez; örneğin `uygulanacak KDV oranı`, `vergilendirilmesi` veya `Kanunları karşısındaki durumu` gibi köksüz kalabilir. "
            "Bu durumda soru bağlamı bozulmadan tamamlanır ve genellikle `nedir` soru eki eklenir. "
            "Örneğin `uygulanacak KDV oranı` ifadesi `uygulanacak KDV oranı nedir` diye; "
            "Örneğin `bahşişlerin vergilendirilmesi hususunda görüş talep edilmektedir` ifadesi `bahşişlerin vergilendirilmesi nedir` diye; "
            "Örneğin `Kanunları karşısındaki durumu hususunda görüş talep edilmektedir` ifadesi `Kanunları karşısındaki durumu nedir` diye soru haline getirilir. "
            "`hususunda görüş talep edilmektedir` gibi kapanış kalıpları soruya eklenmez.\n"
        ),
    }


def _join_notes(*notes: str | None) -> str | None:
    clean = [note.strip() for note in notes if note and note.strip()]
    if not clean:
        return None
    return "\n\n".join(clean)
