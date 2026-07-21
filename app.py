import streamlit as st
import time
import re
from io import BytesIO
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import google.generativeai as genai

# ==========================================
# ตั้งค่าหน้าเว็บ POOM AI SNTC V3
# ==========================================
st.set_page_config(page_title="POOM AI SNTC", page_icon="🤖", layout="centered")
st.title("🤖 POOM AI SNTC V3")
st.write("แอปพลิเคชันช่วยตอบ Google Form อัตโนมัติ (เวอร์ชันส่งภาพวิเคราะห์รวดเดียว ⚡)")

# ==========================================
# ส่วนที่ 1: รับค่าจากผู้ใช้งาน
# ==========================================
with st.expander("⚙️ การตั้งค่าระบบ (คลิกเพื่อซ่อน/แสดง)", expanded=True):
    api_key_input = st.text_input("🔑 ใส่ Gemini API Key ของคุณ:", type="password")
    form_url = st.text_input("🔗 วางลิงก์ Google Form (เฉพาะฟอร์มที่ไม่ต้องล็อกอิน):")

if st.button("🚀 ให้ POOM AI เริ่มทำข้อสอบ", type="primary"):
    if not api_key_input or not form_url.startswith("http"):
        st.error("❌ กรุณาใส่ API Key และลิงก์ฟอร์มให้ถูกต้อง")
    else:
        st.info("🌐 กำลังเปิดบอทบน Cloud กรุณารอสักครู่...")
        
        try:
            genai.configure(api_key=api_key_input)
            
            # --- ค้นหาโมเดลที่รองรับอัตโนมัติ (แก้ปัญหา 404) ---
            working_model_name = 'gemini-1.5-flash' # ค่าเริ่มต้น
            try:
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                flash_models = [m for m in available_models if 'flash' in m]
                if flash_models:
                    working_model_name = flash_models[0]
                else:
                    pro_models = [m for m in available_models if 'pro' in m]
                    if pro_models:
                        working_model_name = pro_models[0]
            except:
                pass
                
            model = genai.GenerativeModel(working_model_name)
            st.success(f"✅ เชื่อมต่อ AI สำเร็จ! (ใช้โมเดล: {working_model_name})")
            
        except Exception as e:
            st.error(f"❌ API Key มีปัญหา: {e}")
            st.stop()
            
        driver = None 
        
        try:
            # ตั้งค่า Chrome ล่องหน
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--lang=th-TH")
            
            options.binary_location = "/usr/bin/chromium"
            service = Service("/usr/bin/chromedriver")
            
            driver = webdriver.Chrome(service=service, options=options)
            driver.get(form_url)
            time.sleep(3)

            # --- 1. ระบบข้ามหน้าแรก (ถ้ามี) ---
            st.info("🔍 กำลังตรวจสอบหน้าเว็บ...")
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

            # --- 2. แคปหน้าจอแบบ Full-Page ครั้งเดียว ---
            total_width = driver.execute_script("return document.body.parentNode.scrollWidth")
            total_height = driver.execute_script("return document.body.parentNode.scrollHeight")
            driver.set_window_size(1280, total_height) # บังคับความกว้าง 1280 ให้ภาพชัด
            time.sleep(1.5) 
            
            screenshot = driver.get_screenshot_as_png()
            full_page_img = Image.open(BytesIO(screenshot))
            st.image(full_page_img, caption="📸 ภาพถ่ายข้อสอบเต็มหน้าจอที่จะส่งให้ AI", use_container_width=True)

            # --- 3. ดึงข้อความและตัวเลือกมาทำสารบัญให้ AI ---
            question_blocks = driver.find_elements(By.XPATH, "//div[@role='listitem']")
            valid_questions = []
            questions_text_for_prompt = ""
            
            for index, block in enumerate(question_blocks):
                heading = block.find_elements(By.XPATH, ".//div[@role='heading']")
                q_text = heading[0].text if heading else "[คำถามจากภาพ]"
                
                radios = block.find_elements(By.XPATH, ".//div[@role='radio']")
                if not radios: continue
                
                choices = [r.get_attribute("data-value") for r in radios if r.get_attribute("data-value")]
                
                # เก็บข้อมูลไว้สำหรับกดคลิกทีหลัง
                valid_questions.append({
                    "q_num": index + 1,
                    "text": q_text,
                    "radios": radios,
                    "choices": choices
                })
                
                # สร้างข้อความไปใบ้ให้ AI
                questions_text_for_prompt += f"ข้อ {index + 1}: {q_text}\nตัวเลือก: {', '.join(choices)}\n\n"

            st.success(f"พบข้อสอบที่สามารถตอบได้ทั้งหมด {len(valid_questions)} ข้อ")

            # --- 4. ส่งรูป + ข้อความ ไปถาม AI รวดเดียวจบ ---
            st.info("🧠 AI กำลังวิเคราะห์ข้อสอบทั้งหมดพร้อมกัน (อาจใช้เวลา 10-20 วินาที)...")
            
            prompt = f"""คุณคือผู้เชี่ยวชาญระดับสูงที่รอบคอบและแม่นยำมาก
นี่คือภาพถ่ายหน้าจอข้อสอบแบบเต็มหน้า และนี่คือข้อความตัวเลือกที่สกัดมาได้:

{questions_text_for_prompt}

คำสั่ง:
1. ให้ดูภาพข้อสอบทั้งหมดจากบนลงล่างอย่างละเอียด
2. วิเคราะห์หาคำตอบที่ถูกต้องที่สุดของแต่ละข้อ โดยต้องเป็นตัวเลือกที่มีอยู่จริงเท่านั้น ห้ามคิดคำตอบใหม่เอง
3. รูปแบบการตอบ ให้ตอบกลับมาเป็นบรรทัด ตามรูปแบบด้านล่างนี้เป๊ะๆ ห้ามมีคำอธิบายเพิ่มเติมใดๆ ทั้งสิ้น:
ข้อ 1: [คำตอบ]
ข้อ 2: [คำตอบ]"""
            
            response = model.generate_content([prompt, full_page_img])
            ai_result = response.text.strip()
            
            # --- 5. แยกแยะคำตอบ และกดตัวเลือก ---
            st.markdown("### 🎯 ผลการวิเคราะห์และเลือกคำตอบ")
            
            # แปลงข้อความ AI ให้กลายเป็น Dictionary เพื่อค้นหาง่ายขึ้น
            answer_dict = {}
            for line in ai_result.split('\n'):
                line = line.strip()
                if line.startswith('ข้อ'):
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        match = re.search(r'\d+', parts[0])
                        if match:
                            answer_dict[int(match.group())] = parts[1].strip()
            
            export_text = "เฉลยข้อสอบจาก POOM AI SNTC V2\n" + ("="*40) + "\n\n"
            
            for item in valid_questions:
                q_num = item["q_num"]
                q_text = item["text"]
                radios = item["radios"]
                
                st.write(f"📝 **ข้อ {q_num}:** {q_text}")
                
                ai_ans = answer_dict.get(q_num)
                if ai_ans:
                    st.info(f"💡 **POOM AI ตอบ:** {ai_ans}")
                    export_text += f"ข้อ {q_num}: {q_text}\nตอบ: {ai_ans}\n\n"
                    
                    # สั่งบอทกดคลิก
                    for r in radios:
                        if r.get_attribute("data-value").strip() == ai_ans:
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", r)
                            time.sleep(0.3)
                            r.click()
                            break
                else:
                    st.warning("⚠️ AI ไม่ได้ส่งคำตอบสำหรับข้อนี้มา")
                st.markdown("---")
                
            # --- 6. ปุ่มดาวน์โหลดไฟล์ ---
            st.download_button(
                label="📥 ดาวน์โหลดเฉลยเป็นไฟล์ Text",
                data=export_text,
                file_name="poom_ai_sntc_v2_answers.txt",
                mime="text/plain"
            )
            st.success("🎉 ทำรายการเสร็จสมบูรณ์!")
            
        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาด: {e}")
        finally:
            if driver is not None:
                driver.quit()
