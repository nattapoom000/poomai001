import streamlit as st
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from google import genai

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="AI Form Solver", page_icon="🤖")
st.title("🤖 AI Form Solver (Online)")
st.write("แอปพลิเคชันช่วยตอบ Google Form อัตโนมัติด้วย Gemini AI")

# --- ส่วนที่ 1: รับค่าจากผู้ใช้งาน ---
st.markdown("### 1. ตั้งค่าการเชื่อมต่อ AI")
api_key_input = st.text_input("🔑 ใส่ Gemini API Key ของคุณ:", type="password", help="รับ API Key ฟรีได้ที่ Google AI Studio (ระบบจะไม่บันทึก Key ของคุณไว้)")

st.markdown("### 2. ลิงก์ข้อสอบ")
form_url = st.text_input("🔗 วางลิงก์ Google Form (เฉพาะฟอร์มที่ไม่ต้องล็อกอิน):")

# --- ส่วนที่ 2: เริ่มทำงาน ---
if st.button("🚀 ให้ AI เริ่มทำข้อสอบ"):
    if not api_key_input:
        st.error("❌ กรุณาใส่ Gemini API Key ก่อนครับ")
    elif not form_url.startswith("http"):
        st.error("❌ กรุณาใส่ลิงก์ Google Form ให้ถูกต้อง")
    else:
        st.info("🌐 กำลังเปิดบอทบน Cloud กรุณารอสักครู่...")
        
        # ตั้งค่า Client ด้วย API Key ที่ผู้ใช้กรอกมา
        try:
            client = genai.Client(api_key=api_key_input)
        except Exception as e:
            st.error(f"❌ API Key มีปัญหา: {e}")
            st.stop()
            
        driver = None # กำหนดตัวแปรไว้ก่อนเพื่อป้องกัน NameError
        
        try:
            # ตั้งค่า Chrome แบบล่องหนสำหรับ Cloud Server
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            
            # ชี้เป้าไปที่ตัวเปิดเบราว์เซอร์ของระบบ Linux โดยตรง (แก้ปัญหาเวอร์ชันไม่ตรง)
            options.binary_location = "/usr/bin/chromium"
            service = Service("/usr/bin/chromedriver")
            
            # เปิด Chrome
            driver = webdriver.Chrome(service=service, options=options)
            driver.get(form_url)
            time.sleep(3)
            
            question_blocks = driver.find_elements(By.XPATH, "//div[@role='listitem']")
            st.success(f"พบบล็อกคำถามทั้งหมด {len(question_blocks)} ข้อ")
            
            # กวาดคำถาม
            for index, block in enumerate(question_blocks):
                heading_elements = block.find_elements(By.XPATH, ".//div[@role='heading']")
                if not heading_elements: continue
                question_text = heading_elements[0].text
                
                radio_buttons = block.find_elements(By.XPATH, ".//div[@role='radio']")
                choices = [r.get_attribute("data-value") for r in radio_buttons if r.get_attribute("data-value")]
                
                if question_text and choices:
                    st.write(f"📝 **ข้อ {index + 1}:** {question_text}")
                    
                    # ส่งถาม Gemini
                    prompt = f"อ่านคำถามและเลือกคำตอบที่ถูกต้องที่สุดเพียง 1 ข้อ\nคำถาม: {question_text}\nตัวเลือก:\n{chr(10).join([f'- {c}' for c in choices])}\nตอบเฉพาะข้อความตัวเลือก ห้ามมีคำอธิบาย"
                    
                    try:
                        response = client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
                        ai_answer = response.text.strip()
                        st.write(f"💡 **AI เลือก:** {ai_answer}")
                        
                        # กดเลือกคำตอบ
                        for radio in radio_buttons:
                            if radio.get_attribute("data-value").strip() == ai_answer:
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", radio)
                                time.sleep(0.5)
                                radio.click()
                                break
                    except Exception as ai_err:
                        st.warning(f"⚠️ ไม่สามารถให้ AI ตอบข้อนี้ได้: {ai_err}")
            
            st.warning("⚠️ บอททำงานเสร็จแล้ว! (บนระบบ Cloud แบบล่องหน โปรแกรมจะไม่สามารถกด Submit ให้ได้นะครับ คุณจะได้เห็นเฉพาะเฉลยที่ AI คิดออกบนหน้าเว็บนี้เท่านั้น)")
            
        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาดในการดึงข้อมูลจากเว็บ: {e}")
        finally:
            # เช็คก่อนว่ามีบอทเปิดอยู่จริงๆ ถึงจะสั่งปิด (แก้ NameError)
            if driver is not None:
                driver.quit()
