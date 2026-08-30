# Chinese Stroke Order Generator (Automated / Serverless Edition)

## Giới thiệu
Đây là phiên bản **Tự Động Hóa 100% (Serverless)** của công cụ tạo ảnh GIF chữ Hán.
Hệ thống sử dụng GitHub Actions làm máy chủ ảo để chạy Puppeteer (vẽ ảnh) và Python (xử lý logic), loại bỏ hoàn toàn sự phụ thuộc vào máy tính cá nhân hoặc Google Colab.

## Luồng hoạt động
1. Đọc danh sách chữ Hán cần tạo từ Google Sheet.
2. Dùng trình duyệt ảo (Chrome/Puppeteer) vẽ từng nét chữ và ghi hình lại (150 khung hình).
3. Dùng FFmpeg ghép thành ảnh GIF hoàn chỉnh.
4. Lưu ảnh GIF thẳng vào mã nguồn trên GitHub để tránh lỗi chặn dung lượng (Quota Limit) của Google Drive đối với Bot.
5. Ghi link tải ảnh (từ GitHub) trả về lại Google Sheet.
6. (Tùy chọn) Mã Google Apps Script trên Sheet sẽ tự động tải file từ link GitHub và ném vào Google Drive cá nhân.

## Hướng dẫn cài đặt lại cho Antigravity (Dành cho Tương lai)

Nếu anh muốn thiết lập lại dự án này từ đầu trên một máy mới, hãy copy câu lệnh này gửi cho **Antigravity**:
> *"Antigravity, hãy đọc file README.md trong thư mục này, sau đó khôi phục lại kho GitHub Actions và thiết lập đường ống tự động tạo chữ Hán cho tôi."*

### Các bước AI (Antigravity) cần thực hiện khi cài đặt lại:
1. Khởi tạo một kho chứa (Repository) mới trên GitHub và đẩy (push) toàn bộ thư mục này lên nhánh `main`.
2. Yêu cầu Người dùng (USER) cung cấp mã **Google Service Account JSON**.
3. Thêm mã JSON đó vào **GitHub Secrets** với tên biến là `GCP_CREDENTIALS`.
4. Hướng dẫn Người dùng chia sẻ quyền **Editor (Người chỉnh sửa)** của file Google Sheet cho địa chỉ email của Service Account.
5. Hướng dẫn Người dùng thiết lập **Google Apps Script** trên Sheet để tự động đồng bộ file GIF từ GitHub về Google Drive (code mẫu nằm trong lịch sử chat).

## Lưu ý về Cấu trúc Code
- `generate.js`: Code vẽ hình chữ Hán (Dùng chuẩn Promise thay vì `page.waitForTimeout` đã bị xóa ở Puppeteer v22+).
- `daily_batch.py`: Script điều phối, đọc Google Sheet, gọi `generate.js`, và điền link.
- `.github/workflows/daily-run.yml`: Trái tim của hệ thống. File cấu hình ra lệnh cho GitHub tự động chạy mỗi ngày lúc 00:00 (Giờ VN).
- `output/`: Thư mục chứa các ảnh GIF xuất ra.
