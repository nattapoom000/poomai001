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
# ตั้งค่าหน้าเว็บ POOM AI SNTC V5
# ==========================================
st.set_page_config(page_title="POOM AI SNTC", page_icon="🤖", layout="centered")
st.title("🤖 POOM AI SNTC V5")
st.write("แอปพลิเคชันสร้างเฉลย Google Form (เวอร์ชันสแกนและสรุปคำตอบอย่างเดียว ⚡)")

# ==========================================
# ส่วนที่ 1: รับค่าจากผู้ใช้งาน
# ==========================================
with st.expander("⚙️ การตั้งค่าระบบ (คลิกเพื่อซ่อน/แสดง)", expanded=True):
    api_key_input = st.text_input("🔑 ใส่ Gemini API Key ของคุณ:", type="password")
    form_url = st.text_input("🔗 วางลิงก์ Google Form (เฉพาะฟอร์มที่ไม่ต้องล็อกอิน):")

if st.button("🚀 ให้ POOM AI เริ่มสแกนข้อสอบ", type="primary"):
    if not api_key_input or not form_url.startswith("http"):
        st.error("❌ กรุณาใส่ API Key และลิงก์ฟอร์มให้ถูกต้อง")
    else:
        st.info("🌐 กำลังเปิดบอทสแกนเนอร์บน Cloud กรุณารอสักครู่...")
        
        try:
            genai.configure(api_key=api_key_input)
            working_model_name = 'gemini-1.5-flash' 
            try:
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                flash_models = [m for m in available_models if 'flash' in m]
                if flash_models:
                    working_model_name = flash_models[0]
            except:
                pass
            model = genai.GenerativeModel(working_model_name)
            st.success(f"✅ เชื่อมต่อ AI สำเร็จ! (ใช้โมเดล: {working_model_name})")
        except Exception as e:
            st.error(f"❌ API Key มีปัญหา: {e}")
            st.stop()
            
        driver = None 
        
        try:
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--lang=th-TH")
            options.add_argument("--window-size=1280,1080")
            
            options.binary_location = "/usr/bin/chromium"
            service = Service("/usr/bin/chromedriver")
            
            driver = webdriver.Chrome(service=service, options=options)
            driver.get(form_url)
            time.sleep(3)

            # --- 1. ระบบข้ามหน้าแรก (ข้ามหน้ากรอกชื่อ เพื่อให้เห็นข้อสอบ) ---
            st.info("🔍 กำลังตรวจสอบหน้าเว็บและทะลวงเข้าสู่หน้าข้อสอบ...")
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
                        break
            except:
                pass 

            # --- 2. กวาดข้อสอบ (วิเคราะห์และสรุปคำตอบเท่านั้น) ---
            question_blocks = driver.find_elements(By.XPATH, "//div[@role='listitem']")
            st.success(f"พบบล็อกคำถามทั้งหมด {len(question_blocks)} ข้อ")
            
            export_text = "เฉลยข้อสอบจาก POOM AI SNTC V5\n" + ("="*40) + "\n\n"
            
            for index, block in enumerate(question_blocks):
                radios = block.find_elements(By.XPATH, ".//div[@role='radio']")
                text_boxes = block.find_elements(By.XPATH, ".//input[@type='text'] | .//textarea")
                
                # ถ้าไม่ใช่ทั้งข้อสอบแบบตัวเลือกและข้อสอบแบบพิมพ์ตอบ ให้ข้ามไป
                if not radios and not text_boxes:
                    continue

                if index > 0:
                    time.sleep(3) # หน่วงเวลา
                    
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", block)
                time.sleep(0.5)
                
                try:
                    block_png = block.screenshot_as_png
                    block_img = Image.open(BytesIO(block_png))
                except:
                    block_img = None
                
                heading = block.find_elements(By.XPATH, ".//div[@role='heading']")
                question_text = heading[0].text if heading else f"[ข้อสอบรูปภาพ ข้อ {index+1}]"
                
                st.markdown("---")
                
                if radios:
                    st.write(f"📝 **ข้อ {index + 1} (ตัวเลือก):** {question_text}")
                    choices = [r.get_attribute("data-value") for r in radios if r.get_attribute("data-value")]
                    prompt = f"""คุณคือผู้เชี่ยวชาญระดับสูง วิเคราะห์ภาพข้อสอบนี้อย่างละเอียด
คำถาม: {question_text}
ตัวเลือกที่มี: {chr(10).join([f'- {c}' for c in choices])}
คำสั่ง: เลือกคำตอบที่ถูกต้องที่สุด ตอบกลับมา "เฉพาะข้อความตัวเลือก" เป๊ะๆ ห้ามมีคำอธิบายเด็ดขาด"""
                else:
                    st.write(f"✍️ **ข้อ {index + 1} (พิมพ์ตอบ):** {question_text}")
                    prompt = f"""คุณคือผู้เชี่ยวชาญระดับสูง วิเคราะห์ภาพและคำถามข้อสอบนี้อย่างละเอียด
คำถาม: {question_text}
คำสั่ง: ตอบคำถามนี้ด้วยข้อความสั้นๆ กระชับ ได้ใจความ และถูกต้องที่สุด ห้ามพิมพ์คำอธิบายหรือคำเกริ่นนำใดๆ ตอบเฉพาะส่วนที่เป็นคำตอบเท่านั้น"""

                if block_img:
                    st.image(block_img, caption="ภาพเฉพาะข้อนี้")
                    contents = [prompt, block_img]
                else:
                    contents = [prompt]
                
                # ส่งถาม AI
                ai_answer = ""
                for attempt in range(1, 4):
                    try:
                        response = model.generate_content(contents)
                        ai_answer = response.text.strip()
                        if not ai_answer:
                            raise ValueError("AI ตอบค่าว่าง")
                        st.info(f"💡 **POOM AI สรุปคำตอบคือ:** {ai_answer}")
                        break
                    except Exception as ai_err:
                        if "429" in str(ai_err) or "quota" in str(ai_err).lower():
                            st.warning(f"⏳ AI ติดลิมิต... รอ 10 วินาที (ครั้งที่ {attempt}/3)")
                            time.sleep(10)
                        else:
                            st.warning(f"⚠️ พยายามถามใหม่... (ครั้งที่ {attempt}/3)")
                            time.sleep(2)
                            
                if not ai_answer:
                    st.error("❌ AI ไม่สามารถตอบข้อนี้ได้")
                    ai_answer = "[ไม่พบคำตอบ]"

                # บันทึกคำตอบลงในข้อความสำหรับ Export (ไม่ต้องสั่งกดคลิกหรือพิมพ์ลงเว็บแล้ว)
                export_text += f"ข้อ {index + 1}: {question_text}\nตอบ: {ai_answer}\n\n"
                        
            # --- 3. ปุ่มดาวน์โหลดเฉลย ---
            st.markdown("---")
            st.download_button(
                label="📥 ดาวน์โหลดไฟล์สรุปคำตอบ (Text)",
                data=export_text,
                file_name="poom_ai_sntc_v5_answers.txt",
                mime="text/plain"
            )
            st.success("🎉 วิเคราะห์และสรุปคำตอบเสร็จสมบูรณ์!")
            
        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาด: {e}")
        finally:
            if driver is not None:
                driver.quit()
