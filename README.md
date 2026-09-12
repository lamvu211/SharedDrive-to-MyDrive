# SharedDrive-to-MyDrive

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/lamvu211/SharedDrive-to-MyDrive/blob/main/Copy_Folder_Google_Drive_to_Google_Drive.ipynb)

> **Lợi ích:** Dữ liệu chuyển trực tiếp giữa các máy chủ của Google với tốc độ cao (~50 - 100 MB/s).  
> **Không cần tải về máy**, không tốn dung lượng ổ cứng.

---

### 📋 4 Bước thực hiện

#### 🔹 Bước 1: Chuẩn bị thư mục trên Google Drive của bạn
1. Mở [Google Drive](https://drive.google.com/) của bạn, bấm **Mới** -> tạo một **Thư mục mới** (ví dụ đặt tên: `Share Folder`).
2. Mở thư mục vừa tạo, copy link trên thanh địa chỉ trình duyệt. Đây là link **Your drive**.
3. Chuẩn bị sẵn **đường link thư mục được chia sẻ** mà bạn muốn copy về. Đây là link **Shared drive**.

> 💡 **Lưu ý:** Không cần thiết phải share folder nhận file.

#### 🔹 Bước 2: Bật ô "Input" (Nhập liên kết)
1. Bấm nút **[Open in Colab](https://colab.research.google.com/github/lamvu211/SharedDrive-to-MyDrive/blob/main/Copy_Folder_Google_Drive_to_Google_Drive.ipynb)** ở trên.
2. Bấm nút **Play (▶️)** ở góc trái ô **Input** bên dưới.
3. Nếu hiện bảng cảnh báo của Google (*Warning: This notebook was not authored by Google*), bấm chọn **"Vẫn chạy" (Run Anyway)**.
4. Điền thông tin vào các ô hiện ra:
   * **Your drive**: Dán link thư mục nhận trên Drive của bạn (ở Bước 1).
   * **Shared drive**: Dán link thư mục được người khác chia sẻ.
   * **Số luồng**: Để nguyên **5 (Khuyên dùng - Nhanh)**.
   * **Dung lượng tối đa (GB)**: Giữ nguyên **700** (hoặc giảm bớt nếu muốn giới hạn).
   * **Bỏ file/thư mục có chứa**: Bỏ trống nếu muốn copy toàn bộ.

#### 🔹 Bước 3: Bật ô "Run" (Bắt đầu sao chép)
1. Bấm nút **Play (▶️)** ở góc trái ô **Run**.
2. Nếu Google hiện cửa sổ yêu cầu kết nối tài khoản:
   * Bấm **"Kết nối với Google Drive" (Connect to Google Drive)**.
   * Chọn tài khoản Google Drive của bạn và bấm **"Cho phép" (Allow)**.

#### 🔹 Bước 4: Chờ nhận thành quả
* Màn hình sẽ hiển thị tiến độ thời gian thực: số file đã chép, dung lượng và tốc độ.
* Khi copy xong, bảng **TỔNG KẾT: Hoàn thành 100%** sẽ xuất hiện. Bạn chỉ cần vào lại Google Drive của mình để kiểm tra file.

---

### ℹ️ Thông tin phát triển & Tối ưu

Notebook này được phát triển thêm từ dự án của Vtechtin.  
Link bài viết gốc: https://vtechtin.com/copy-file-folder-tu-google-drive-khac-ve-cua-minh/

Code đã được tối ưu ở một số vấn đề:

| Tiêu chí | Code cũ | Code mới tối ưu |
| :--- | :--- | :--- |
| **Tốc độ xử lý** | Tuần tự đơn luồng (chậm) | Đa luồng song song (5 luồng), đạt ~90 MB/s |
| **Kiểm tra file trùng** | $O(N)$ gọi API từng file một | Bộ nhớ đệm $O(1)$ trên RAM, giảm 90% API calls |
| **Số mục quét/trang** | Mặc định 100 mục/lần | Tối đa 1.000 mục/lần (`pageSize=1000`) |
| **Giao diện tiến độ** | In tràn màn hình (đơ trình duyệt) | Ghi đè 1 dòng duy nhất kèm bảng tổng kết |
| **Độ ổn định** | Dễ crash khi gặp lỗi vặt | Tự thử lại (Retry Backoff) khi Google bận |
