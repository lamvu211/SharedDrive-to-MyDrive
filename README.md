# SharedDrive-to-MyDrive

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/lamvu211/SharedDrive-to-MyDrive/blob/main/Copy_Folder_Google_Drive_to_Google_Drive.ipynb)

Tool sao chép toàn bộ file và thư mục từ Google Drive khác (hoặc Shared Drive) sang Google Drive cá nhân với tốc độ cao (~50 - 100 MB/s), trực tiếp giữa các máy chủ Google, không tốn ổ cứng và băng thông mạng cá nhân.

---

## 🚀 Hướng Dẫn Sử Dụng (Dành Cho Người Không Biết Code)

### 🔹 Bước 1: Chuẩn bị thư mục nhận
1. Mở [Google Drive](https://drive.google.com/) của bạn, tạo một **Thư mục mới** (ví dụ: `Thu_Muc_Nhan`).
2. Mở thư mục vừa tạo, sao chép link trên trình duyệt (đây là **Your drive**).
3. Lấy sẵn đường link thư mục được người khác chia sẻ (đây là **Shared drive**).

### 🔹 Bước 2: Bật ô "Input" (Nhập liên kết)
1. Bấm nút **[Open in Colab](https://colab.research.google.com/github/lamvu211/SharedDrive-to-MyDrive/blob/main/Copy_Folder_Google_Drive_to_Google_Drive.ipynb)** ở trên.
2. Bấm nút **Play (▶️)** ở ô **Input**. Nếu Google hiện cảnh báo mã nguồn lạ, chọn **"Vẫn chạy" (Run Anyway)**.
3. Điền link vào các ô:
   - **Your drive**: Link thư mục của bạn (ở Bước 1).
   - **Shared drive**: Link thư mục người khác chia sẻ.
   - Các thông số khác để nguyên mặc định (5 luồng, 700 GB).

### 🔹 Bước 3: Bật ô "Run" (Bắt đầu sao chép)
1. Bấm nút **Play (▶️)** ở ô **Run**.
2. Khi hiện bảng yêu cầu quyền, chọn **"Kết nối với Google Drive" (Connect to Google Drive)** -> chọn tài khoản Google của bạn -> bấm **"Cho phép" (Allow)**.

### 🔹 Bước 4: Chờ hoàn thành
* Màn hình hiển thị tiến độ thời gian thực. Khi thấy thông báo **Hoàn thành 100%**, toàn bộ file đã nằm trong Google Drive của bạn.
