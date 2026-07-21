import streamlit as st
import time
from io import BytesIO
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import google.generativeai as genai

# ==========================================
# ตั้งค่าหน้าเว็บตามชื่อใหม่
# ==========================================
st.set_page_config(page_title="POOM AI SNTC", page_icon="🤖")
st.title("🤖 POOM AI SNTC")
st.write("แอปพลิเคชันช่วยตอบ Google Form อัตโนมัติ (รองรับรูปภาพและภาษาไทย)")

# ==========================================
# ส่วนที่ 1: รับค่าจากผู้ใช้งาน
# ==========================================
st.markdown("### 1. ตั้งค่าการเชื่อมต่อ AI")
api_key_input = st.text_input("🔑 ใส่ Gemini API Key ของคุณ:", type="password")

st.markdown("### 2. ลิงก์ข้อสอบ")
form_url = st.text_input("🔗 วางลิงก์ Google Form (เฉพาะฟอร์มที่ไม่ต้องล็อกอิน):")

# ==========================================
# ส่วนที่ 2: เริ่มทำงาน
# ==========================================
if st.button("🚀 ให้ POOM AI เริ่มทำข้อสอบ"):
    if not api_key_input:
        st.error("❌ กรุณาใส่ Gemini API Key ก่อนครับ")
    elif not form_url.startswith("http"):
        st.error("❌ กรุณาใส่ลิงก์ Google Form ให้ถูกต้อง")
    else:
        st.info("🌐 กำลังเปิดบอทบน Cloud กรุณารอสักครู่...")
        
        # ตั้งค่า AI และค้นหาโมเดลที่รองรับอัตโนมัติ (แก้ปัญหา Error 404)
        try:
            genai.configure(api_key=api_key_input)
            
            # ค้นหาโมเดลที่ใช้งานได้
            working_model_name = 'gemini-pro' # ค่าเริ่มต้น
            try:
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                for name in available_models:
                    if 'flash' in name:
                        working_model_name = name
                        break
            except:
                pass
                
            model = genai.GenerativeModel(working_model_name)
            st.success(f"✅ เชื่อมต่อ AI สำเร็จ! (ใช้โมเดล: {working_model_name})")
        except Exception as e:
            st.error(f"❌ API Key มีปัญหา: {e}")
            st.stop()
            
        driver = None 
        
        try:
            # ตั้งค่า Chrome ล่องหน พร้อมบังคับให้แสดงผลเป็นภาษาไทย
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--lang=th-TH") # บังคับภาษาไทย
            
            options.binary_location = "/usr/bin/chromium"
            service = Service("/usr/bin/chromedriver")
            
            driver = webdriver.Chrome(service=service, options=options)
            driver.get(form_url)
            time.sleep(3)

            # ---------------------------------------------------------
            # 1. ระบบจัดการหน้าแรก (ข้ามหน้า)
            # ---------------------------------------------------------
            st.info("🔍 ตรวจสอบโครงสร้างหน้าเว็บ (ข้ามหน้าอัตโนมัติหากมี)...")
            try:
                text_inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='email'] | //textarea")
                for txt in text_inputs:
                    if txt.is_displayed():
                        txt.send_keys("ทดสอบ")
                
                next_buttons = driver.find_elements(By.XPATH, "//div[@role='button']//span[contains(text(), 'ถัดไป') or contains(text(), 'Next')]/ancestor::div[@role='button']")
                for btn in next_buttons:
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                        time.sleep(1)
                        btn.click()
                        time.sleep(3) 
                        st.success("➡️ บอทข้ามหน้าแรกมายังหน้าข้อสอบสำเร็จ!")
                        break
            except Exception:
                pass 
            
            # ---------------------------------------------------------
            # 2. แคปหน้าจอ
            # ---------------------------------------------------------
            st.markdown("### 📸 ภาพหน้าจอที่บอทมองเห็น ณ ปัจจุบัน")
            screenshot = driver.get_screenshot_as_png()
            st.image(screenshot, caption="ตอนนี้เซิร์ฟเวอร์ติดตั้งฟอนต์ไทยแล้ว ควรอ่านออกได้ปกติครับ")

            # ---------------------------------------------------------
            # 3. เริ่มกวาดข้อสอบ
            # ---------------------------------------------------------
            question_blocks = driver.find_elements(By.XPATH, "//div[@role='listitem']")
            st.success(f"พบบล็อกคำถามทั้งหมด {len(question_blocks)} ข้อ")
            
            export_text = "เฉลยข้อสอบจาก POOM AI SNTC\n" + ("="*30) + "\n\n"
            
            for index, block in enumerate(question_blocks):
                # หน่วงเวลา 3 วินาทีต่อข้อ ป้องกัน Rate Limit
                if index > 0:
                    time.sleep(3)
                    
                heading_elements = block.find_elements(By.XPATH, ".//div[@role='heading']")
                question_text = heading_elements[0].text if heading_elements else ""
                
                # ระบบดึงรูปภาพ (Vision)
                img_elements = block.find_elements(By.XPATH, ".//img")
                img_content = None
                if img_elements:
                    try:
                        img_png = img_elements[0].screenshot_as_png
                        img_content = Image.open(BytesIO(img_png))
                        st.caption(f"📸 (ตรวจพบรูปภาพในข้อ {index + 1} ส่งให้ AI วิเคราะห์ด้วย)")
                    except:
                        pass
                
                radio_buttons = block.find_elements(By.XPATH, ".//div[@role='radio']")
                if not radio_buttons: continue
                choices = [r.get_attribute("data-value") for r in radio_buttons if r.get_attribute("data-value")]
                
                display_q = question_text if question_text else "[ข้อสอบรูปภาพ]"
                if choices:
                    st.write(f"📝 **ข้อ {index + 1}:** {display_q}")
                    
                    prompt = f"อ่านคำถามและเลือกคำตอบที่ถูกต้องที่สุดเพียง 1 ข้อ\nคำถาม: {display_q}\nตัวเลือก:\n{chr(10).join([f'- {c}' for c in choices])}\nตอบเฉพาะข้อความตัวเลือก ห้ามมีคำอธิบาย"
                    
                    contents_to_send = [prompt]
                    if img_content:
                        contents_to_send.append(img_content)
                    
                    # ระบบป้องกัน API ลิมิต (Retry Logic)
                    ai_answer = ""
                    for attempt in range(1, 4):
                        try:
                            response = model.generate_content(contents_to_send)
                            ai_answer = response.text.strip()
                            st.write(f"💡 **AI เลือก:** {ai_answer}")
                            break
                        except Exception as ai_err:
                            err_str = str(ai_err).lower()
                            if "429" in err_str or "quota" in err_str or "exhausted" in err_str:
                                st.warning(f"⏳ AI ทำงานเร็วเกินไป ติดลิมิต... รอ 10 วินาที (ครั้งที่ {attempt}/3)")
                                time.sleep(10)
                            else:
                                st.warning(f"⚠️ AI ตอบไม่ได้: {ai_err}")
                                break
                    
                    if ai_answer:
                        export_text += f"ข้อ {index + 1}: {display_q}\nตอบ: {ai_answer}\n\n"
                        
                        for radio in radio_buttons:
                            if radio.get_attribute("data-value").strip() == ai_answer:
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", radio)
                                time.sleep(0.5)
                                radio.click()
                                break
            
            # ---------------------------------------------------------
            # 4. ดาวน์โหลดไฟล์เฉลย
            # ---------------------------------------------------------
            st.markdown("### 💾 บันทึกเฉลย")
            st.download_button(
                label="📥 ดาวน์โหลดเฉลยเป็นไฟล์ Text",
                data=export_text,
                file_name="poom_ai_sntc_answers.txt",
                mime="text/plain"
            )
            
            st.success("🎉 บอท POOM AI SNTC ทำงานเสร็จสมบูรณ์!")
            
        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")
        finally:
            if driver is not None:
                driver.quit()
