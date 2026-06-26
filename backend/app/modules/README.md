## Modül Organizasyonu (taslak)

Bu klasör, iş alanlarını modüllere ayırmak için ayrılmıştır. Bu adımda endpoint/servis kodu yazılmadı.

Önerilen modüller:

- `auth/`: JWT login, token refresh, parola hash doğrulama
- `users/`: kullanıcı CRUD, rol yönetimi, profil
- `documents/`: belge ingest, belge havuzu/queue, split mantığı
- `training/`: eğitim içerikleri (ilk 400), kullanım kılavuzu örnekleri
- `quiz/`: mini sınav (soru bankası, attempt kaydı, geçme kuralları)
- `labeling/`: gerçek etiketleme kayıtları, sorular, cevap alanı
- `admin/`: admin ekranları için backend tarafı (yetkilendirme + yönetim)
- `export/`: CSV/Excel export için sorgular ve dönüştürme (normalize -> wide)
- `dashboard/`: istatistikler, ilerleme metrikleri

