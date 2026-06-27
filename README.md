---
title: TaxLabelTR
sdk: docker
app_port: 7860
---

# TaxLabelTR — Özelge Etiketleme Platformu

Türk vergi **özelgelerinin** (mukteza) yapay zekâ eğitimi için soru/cevap formatında
etiketlendiği uçtan uca bir web uygulaması. Etiketleyiciler her özelge metninden
**soru(lar)ı** ve **cevabı** çıkarır; sistem kalite kontrolü, ilerleme takibi ve
oyunlaştırma ile süreci yönetir.

> **Tek etiket garantisi:** Her özelge belgesi yalnızca **tek bir kullanıcı**
> tarafından etiketlenir. Bu hem uygulama hem de veritabanı seviyesinde güvence altındadır
> (bkz. [Etiketleme akışı ve tek-etiket garantisi](#etiketleme-akışı-ve-tek-etiket-garantisi)).

---

## İçindekiler
- [Özellikler](#özellikler)
- [Teknoloji yığını](#teknoloji-yığını)
- [Proje yapısı](#proje-yapısı)
- [Kurulum](#kurulum)
- [Ortam değişkenleri](#ortam-değişkenleri)
- [Veritabanı ve migration](#veritabanı-ve-migration)
- [Çalıştırma](#çalıştırma)
- [Veri içe aktarımı](#veri-içe-aktarımı)
- [Etiketleme akışı ve tek-etiket garantisi](#etiketleme-akışı-ve-tek-etiket-garantisi)
- [Roller](#roller)
- [Dağıtım](#dağıtım)
- [Güvenlik notları](#güvenlik-notları)

---

## Özellikler

- **Kimlik doğrulama:** JWT tabanlı kayıt/giriş, rol bazlı yetkilendirme.
- **Eğitim + sınav:** Etiketlemeye başlamadan önce kullanıcı eğitim kılavuzunu okur ve
  mini sınavı geçmek zorundadır (`exam_passed`). Geçme notu yapılandırılabilir (varsayılan 80).
- **Belge kuyruğu:** Etiketleyiciye sıradaki uygun özelge atanır; belge çekildiğinde
  o kullanıcıya **kiralanır** (rezervasyon) ve başkasına gösterilmez.
- **Kalite kontrolü:** Soru/cevap girişlerinde Türkçeye özel kontroller — minimum içerik,
  belge metniyle örtüşme, rastgele/tekrar eden metin tespiti, talep-bitiş ve kapanış
  kalıplarının yanlış alana girilmesine karşı uyarılar.
- **Oyunlaştırma:** Günlük ilerleme, "ejderha" ödülleri (eşik bazlı), liderlik tablosu.
- **Yönetici paneli:** Kullanıcı yönetimi, JSON ile toplu veri yükleme, kayıtların
  görüntülenmesi ve dışa aktarımı (Excel/JSON).
- **Tek SPA dağıtımı:** Backend, derlenmiş React arayüzünü (`frontend/dist`) statik olarak servis eder.

---

## Teknoloji yığını

| Katman | Teknolojiler |
|---|---|
| **Backend** | Python, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2 |
| **Veritabanı** | PostgreSQL (Neon) |
| **Kimlik** | JWT (python-jose), bcrypt |
| **Frontend** | React 18, Vite, React Router, Axios |
| **Veri/Export** | pandas, openpyxl, BeautifulSoup4 |
| **Dağıtım** | Render / Docker (HuggingFace Spaces uyumlu) |

---

## Proje yapısı

```
TaxLabelTR/
├── backend/
│   ├── app/
│   │   ├── routers/        # API uçları: auth, users, training, quiz, documents, labeling, admin
│   │   ├── services/       # iş mantığı (labeling, document, quiz, admin, export, ...)
│   │   ├── db/models/      # SQLAlchemy modelleri
│   │   ├── schemas/        # Pydantic şemaları
│   │   ├── auth/           # JWT, bağımlılıklar
│   │   └── main.py         # FastAPI uygulaması (frontend'i de servis eder)
│   ├── alembic/versions/   # veritabanı migration'ları
│   ├── scripts/            # bakım/içe-aktarma yardımcı scriptleri
│   └── requirements.txt
├── frontend/
│   └── src/                # React sayfaları, bileşenler, API istemcisi
├── render.yaml             # Render dağıtım yapılandırması
└── Dockerfile
```

---

## Kurulum

### Önkoşullar
- Python 3.11+
- Node.js 18+
- Bir PostgreSQL veritabanı (örn. ücretsiz [Neon](https://neon.tech))

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
cp .env.neon.example .env        # ardından .env içini kendi değerlerinle doldur
```

### Frontend

```bash
cd frontend
npm install
```

---

## Ortam değişkenleri

`backend/.env` dosyasında tanımlanır (örnek için `backend/.env.neon.example`):

| Değişken | Açıklama |
|---|---|
| `DATABASE_URL` | PostgreSQL bağlantı dizesi (`postgresql://kullanıcı:şifre@host/db?sslmode=require`) |
| `SECRET_KEY` | JWT imzalama anahtarı (uzun, rastgele) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token geçerlilik süresi (varsayılan 1440) |
| `ADMIN_USERNAME` / `ADMIN_EMAIL` / `ADMIN_PASSWORD` | İlk yönetici hesabı (ilk açılışta otomatik oluşturulur) |
| `QUIZ_PASSING_SCORE` | Sınav geçme notu (varsayılan 80) |
| `CORS_ORIGINS` | İzinli origin'ler (virgülle ayrılır; `*` tümü) |
| `JSON_UPLOAD_MAX_MB` | Yönetici JSON yükleme üst sınırı (MB) |

> ⚠️ `.env` dosyası **asla** sürüm kontrolüne eklenmez (`.gitignore` ile dışlanmıştır).

---

## Veritabanı ve migration

Şema **Alembic** ile yönetilir.

```bash
cd backend
alembic upgrade head        # şemayı en güncel sürüme getir
alembic current             # mevcut sürümü göster
alembic revision -m "..."   # yeni migration oluştur
```

İlk açılışta uygulama, ilk yönetici hesabını ve temel seed verilerini otomatik kurar
(`ensure_initial_admin`, `ensure_seed_data`).

---

## Çalıştırma

**Geliştirme (iki ayrı süreç):**

```bash
# 1) Backend
cd backend
uvicorn app.main:app --reload

# 2) Frontend (ayrı terminal)
cd frontend
npm run dev
```

**Üretim benzeri (tek süreç):** Frontend'i derle, backend onu servis etsin.

```bash
cd frontend && npm run build      # frontend/dist üretir
cd ../backend && uvicorn app.main:app
```

API uçları `/api` öneki altındadır; interaktif dokümantasyon `/docs` adresindedir.

---

## Veri içe aktarımı

Özelge verisi (`ozelge_veri.json` vb.) yönetici panelinden JSON yükleme ile veya
`backend/scripts/import_json.py` ile içe aktarılır. İki tür belge desteklenir:

- **Annotation (etiketlenecek):** Etiketleyicilere dağıtılan ham özelgeler.
- **Training (altın küme):** Soru/cevabı önceden belirlenmiş örnekler.

İçe aktarımda belgeler `evrak_id` (evrakOid) üzerinden tekilleştirilir.

> Büyük veri dosyaları (`ozelge_veri.json`, `labelled_questions.json`) `.gitignore`
> ile depodan hariç tutulur.

---

## Etiketleme akışı ve tek-etiket garantisi

1. Kullanıcı eğitim sınavını geçer (`require_exam_passed`).
2. `GET /api/documents/next` ile sıradaki belgeyi alır. Belge o kullanıcıya **kiralanır**
   (rezervasyon); kira süresi (30 dk) dolana ya da belge etiketlenene kadar başka
   kullanıcıya gösterilmez. Eş zamanlı isteklerde `FOR UPDATE SKIP LOCKED` ile her
   kullanıcıya **farklı** belge düşer.
3. Kullanıcı soru/cevabı girer, kalite kontrolünden geçer ve kaydeder.

**Bir belge yalnızca tek kişi tarafından etiketlenebilir.** Bu iki katmanla güvence altındadır:

- **Uygulama katmanı:** Kayıt anında, belge için *herhangi bir kullanıcının* kaydı varsa
  yeni kayıt reddedilir (`409`).
- **Veritabanı katmanı:** `labeling_records.document_id` üzerinde **kısmi unique index**
  ile belge başına en fazla bir kayıt fiziksel olarak zorlanır; tam eş zamanlı yarış
  durumunda bile ikinci kayıt veritabanı tarafından reddedilir.

> Not: Bu kuralın getirildiği migration'dan önce oluşmuş eski mükerrer kayıtlar, geçmiş
> veriye dokunulmaması için bilinçli olarak muaf tutulmuştur.

---

## Roller

| Rol | Yetkiler |
|---|---|
| **labeler** | Eğitim/sınav, belge etiketleme, kendi kayıtları, liderlik tablosu |
| **admin** | Tüm etiketleyici yetkileri + kullanıcı yönetimi, veri yükleme, tüm kayıtlar, dışa aktarım |

---

## Dağıtım

`render.yaml` ile Render üzerinde tanımlıdır:
- Backend `backend/` kök dizininden çalışır (`pip install -r requirements.txt`, `start.sh`).
- Gizli değerler (`DATABASE_URL`, `ADMIN_*`, `CORS_ORIGINS`) Render ortam değişkenleri
  olarak verilir (`sync: false`); `SECRET_KEY` otomatik üretilir.
- Frontend derlenip backend tarafından statik servis edilir.

Depo ayrıca Docker (`Dockerfile`) ve HuggingFace Spaces (`app_port: 7860`) ile uyumludur.

---

## Güvenlik notları

- Sırlar yalnızca `.env` / dağıtım ortam değişkenlerinde tutulur; depoya **eklenmez**.
- Üretimde `CORS_ORIGINS` `*` yerine gerçek alan adlarıyla **daraltılmalıdır**.
- Veritabanı parolası bir kez bile depoya/sohbete sızdıysa **döndürülmelidir** (rotate).
