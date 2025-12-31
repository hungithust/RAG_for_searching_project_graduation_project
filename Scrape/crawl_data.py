import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# --- 1. CẤU HÌNH TÀI KHOẢN ---
EMAIL_HUST = "xxxxxx@sis.hust.edu.vn"
PASSWORD_HUST = "xxxx"

# --- 2. KHỞI TẠO CHROME DRIVER ---
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized") # Mở rộng màn hình
options.add_argument("--disable-notifications") # Tắt thông báo trình duyệt
# options.add_argument("--headless") # Bỏ comment nếu muốn chạy ngầm sau khi code đã ổn

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 20) # Thời gian chờ tối đa 20s

all_data = []

try:
    # --- 3. QUY TRÌNH ĐĂNG NHẬP ---
    print("🚀 [1/6] Truy cập trang chủ QLDT...")
    driver.get("https://qldt.hust.edu.vn/")

    # Click nút Login
    wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btn-login-main-style"))).click()

    # Click nút Office 365
    print("👉 [2/6] Chọn đăng nhập Office 365...")
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".social-btn.office"))).click()

    # Nhập Email
    print("👉 [3/6] Nhập Email...")
    email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
    email_input.send_keys(EMAIL_HUST)
    email_input.send_keys(Keys.ENTER)

    # Nhập Password
    print("👉 [4/6] Nhập Password...")
    # Chờ 1 chút để chuyển form
    time.sleep(3) 
    pass_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
    pass_input.send_keys(PASSWORD_HUST)
    
    # Click nút Sign in
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "span[class='submit']"))).click()

    # Xử lý bước "Stay signed in?" (Có thể có hoặc không)
    print("👉 [5/6] Xác nhận duy trì đăng nhập...")
    try:
        # Chờ nút checkbox xuất hiện (tối đa 5s thôi để đỡ tốn time nếu không có)
        WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='checkbox']"))).click()
        driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
    except:
        print("   -> Bỏ qua bước xác nhận (hoặc không hiện).")

    # Chờ quay về trang trường
    # wait.until(EC.url_contains("qldt.hust.edu.vn"))
    print("✅ Đăng nhập thành công!")
    time.sleep(5)
    # --- 4. VÀO TRANG ĐỒ ÁN & FILTER ---
    print("🔄 [6/6] Vào trang danh sách đồ án...")
    driver.get("https://qldt.hust.edu.vn/students/project/topic")
    
    # Filter: Click vào div chọn bộ môn
    print("   -> Đang Filter...")
    filter_div = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".filter-form-item.item-select-department")))
    filter_div.click()
    print("   -> Đã click vào filter.")
    # Click vào Dropdown (dùng class bạn cung cấp)
    time.sleep(1)
    # dropdown = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'ant-select') and contains(@class, 'ant-select-in-form-item')]")))
    # dropdown = wait.until(EC.element_to_be_clickable((By.ID, "departmentId"))) #success
    # dropdown.click()
    # print("   -> Đã click vào dropdown. ")
    
    # Chọn option Khoa/Bộ môn (ID: departmentId_list_1)
    try:
        option = wait.until(EC.element_to_be_clickable((By.ID, "departmentId_list_1")))
        option.click()
        print("   -> Đã chọn bộ môn, chờ dữ liệu load...")
    except:
        print("   -> Không tìm thấy option bộ môn.")

    # Chờ bảng dữ liệu cập nhật
    time.sleep(3) 

    # --- 5. CÀO DỮ LIỆU & PHÂN TRANG ---
    
    # Lặp từ trang 1 đến trang 6
    for page in range(1, 7): 
        print(f"\n📄 Đang xử lý TRANG {page}...")
        
        # Lấy lại danh sách các dòng tr (tránh lỗi Stale Element)
        rows = wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "tr")))
        # Bỏ dòng đầu tiên nếu là header (thường dòng 0 là header)
        if len(rows) > 0 and "th" in rows[0].get_attribute("innerHTML"):
            data_rows = rows[1:]
        else:
            data_rows = rows

        print(f"   -> Tìm thấy {len(data_rows)} dòng dữ liệu.")

        for i, row in enumerate(data_rows):
            try:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) < 4: continue # Bỏ qua dòng trống
                
                # 1. Thứ tự
                c_order = cols[0].text.strip()
                
                # 2. Giảng viên (trong span)
                try:
                    c_lecturer = cols[1].find_element(By.TAG_NAME, "span").text.strip()
                except: c_lecturer = cols[1].text.strip()
                
                # 3. Tên đề tài & Chi tiết
                c_topic = ""
                c_detail = ""
                try:
                    c_topic = cols[2].find_element(By.TAG_NAME, "p").text.strip()
                    
                    # Xử lý nút "Chi tiết" (div role='button')
                    try:
                        # Tìm nút button trong cột 3
                        btn_detail = cols[2].find_element(By.CSS_SELECTOR, "div[role='button']")
                        
                        # Click bằng JS để chắc ăn
                        driver.execute_script("arguments[0].click();", btn_detail)
                        time.sleep(0.5)
                        # Chờ nội dung chi tiết hiện ra (class 'item-desc-right')
                        # detail_elm = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "item-desc-right")))
                        # c_detail = detail_elm.text.strip()
                        
                        # fix lỗi lặp lại detail đầu tiên nhiều lần
                        # 4. Tìm thẻ div nội dung là ANH EM (Sibling) của nút bấm
                        # XPath: following-sibling::div tìm thẻ div nằm ngay sau btn_detail cùng cấp
                        content_div = btn_detail.find_element(By.XPATH, "following-sibling::div[contains(@class, 'ant-collapse-content-active')]")
                        
                        # 5. Lấy thẻ p.item-desc-right nằm TRONG thẻ div anh em đó
                        detail_p = content_div.find_element(By.CSS_SELECTOR, "p.item-desc-right")
                        c_detail = detail_p.text.strip()
                        # QUAN TRỌNG: Đóng popup hoặc click ra ngoài để trả lại màn hình cho dòng tiếp theo
                        # Cách đơn giản: Gửi phím ESCAPE vào body
                        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                        time.sleep(0.5) # Chờ popup đóng
                        
                    except NoSuchElementException:
                        pass # Không có nút xem thêm thì thôi
                except: pass
                
                # 4. Loại đồ án (ghép text các span)
                c_type = ""
                try:
                    spans = cols[3].find_elements(By.TAG_NAME, "span")
                    c_type = ", ".join([s.text.strip() for s in spans])
                except: pass

                # Lưu
                all_data.append({
                    "Order": c_order,
                    "GiangVien": c_lecturer,
                    "TenDeTai": c_topic,
                    "ChiTiet": c_detail,
                    "LoaiDoAn": c_type
                })
                print(f"      + Lấy xong: {c_topic[:30]}...")

            except Exception as r_e:
                print(f"      ! Lỗi dòng {i}: {r_e}")

        # --- CHUYỂN TRANG (NEXT PAGE) ---
        if page < 6:
            next_page_num = page + 1
            print(f"➡️ Đang chuyển sang trang {next_page_num}...")
            
            try:
                # Tìm thẻ li có title="2", "3"...
                # Selector: li[title='2'] -> button
                next_li_xpath = f"//li[@title='{next_page_num}']//button"
                next_btn = driver.find_element(By.XPATH, next_li_xpath)
                
                # Scroll tới nút đó và click
                driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", next_btn)
                
                # Chờ loading quay quay hoặc chờ dữ liệu thay đổi
                time.sleep(3)
                
            except Exception as e:
                print(f"⚠️ Không tìm thấy nút trang {next_page_num} hoặc lỗi click. Dừng tại đây.")
                break

except Exception as e:
    print(f"❌ Lỗi chương trình: {e}")

finally:
    # --- 6. LƯU FILE ---
    print(f"\n📊 Tổng cộng: {len(all_data)} đề tài.")
    if all_data:
        df = pd.DataFrame(all_data)
        df.to_csv("DoAn_HUST_Chrome.csv", index=False, encoding="utf-8-sig")
        print("💾 Đã lưu file: DoAn_HUST_Chrome.csv")
    
    # driver.quit() # Tắt dòng này nếu muốn giữ trình duyệt để debug