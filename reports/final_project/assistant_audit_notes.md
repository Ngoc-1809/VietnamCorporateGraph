# Rà soát hỗ trợ bằng AI cho snapshot cuối kỳ

Mẫu cố định của snapshot `20261120-144636-gate-v2` gồm 200 cạnh dùng trong ứng dụng, 80 `QUARANTINE` và 20 cạnh bị bộ lọc ứng dụng loại. File mẫu local: `quality_sample_20261120-144636.csv`. **Chưa có người gán nhãn độc lập:** không được tính các nhận xét dưới đây thành gold precision hoặc kết luận đã đạt 90%.

Trợ lý đã đọc **toàn văn lưu trong `data/staging/staging.sqlite`** cho sáu bài dưới đây, so với chủ thể, loại quan hệ, đối tượng và câu chứng cứ của từng cạnh. Cả sáu cạnh đều không được bài hỗ trợ ở đúng hai đầu/loại quan hệ; chúng được đưa vào `config/final_project_exclusions.csv` để loại khỏi snapshot ứng dụng. Dữ liệu aggregate và tier QA nguồn không bị sửa.

| Article ID | Edge ID | Cạnh sai | Lý do |
|---|---|---|---|
| `03f5643179a12579` | `af9dda07516ebb80` | Bùi Minh Tân `CEO_OF` Tổng Công ty Điện lực TKV | Bài ghi **Phó** Tổng Giám đốc DTK, đồng thời là Chủ tịch HĐQT NCP. Không phải CEO DTK. |
| `a48fd4e99c7d440e` | `b59ae3f76197350c` | CTCP Đông Á `PROSECUTED_BY` Bộ Công an | Bài ghi khởi tố **vụ án** xảy ra tại Ngân hàng Đông Á và khởi tố các cá nhân; không truy tố công ty này. |
| `3aec8c77748447d4` | `940c82942a180684` | Chu Tiến Dũng `CEO_OF` SCB | Bài ghi ông là cựu Tổng Giám đốc **CNS**, không phải Ngân hàng TMCP Sài Gòn. |
| `d299754a671996c2` | `3697887c4c37f3b4` | Vietcombank `PARTNERS_WITH` VNSC | Đối tác ký thỏa thuận là **VCBF**, công ty quản lý quỹ có Vietcombank góp vốn; không phải chính ngân hàng. |
| `ce22a71dc8ab48b0` | `2ce7c4fd73fa536e` | Tổng Công ty Miền Trung `SUBSIDIARY_OF` Đất Xanh | Bài nói **CTCP Đất Xanh Miền Trung** là công ty con của Đất Xanh; node chủ thể bị nối nhầm. |
| `27fce55506a01617` | `8b1f93bd57d018d7` | Lý Lương Hồng `CEO_OF` Công ty Điện Quang | Bà được bổ nhiệm làm Tổng Giám đốc **DQSmart**, một công ty con; không phải công ty mẹ Điện Quang. |

Các lỗi cùng nhắc hai rủi ro cần kiểm thêm trong mẫu 200 cạnh: chức danh gần nghĩa (`Phó Tổng Giám đốc` khác `Tổng Giám đốc`) và alias/công ty mẹ–con bị liên kết về nhầm ID. Chỉ sau khi hai thành viên đọc độc lập toàn bài, giải quyết bất đồng và điền `review_mode=HUMAN_FULL_ARTICLE` mới chạy `python -m vckg.final_project.quality_audit evaluate` để báo precision và khoảng tin cậy.
