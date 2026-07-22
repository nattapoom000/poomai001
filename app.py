import streamlit as st
import time
import datetime
from io import BytesIO
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import google.generativeai as genai
from openai import OpenAI
import zipfile

# ==========================================
# ตั้งค่าหน้าเว็บ POOM AI SNTC V6
# ==========================================
st.set_page_config(page_title="POOM AI SNTC", page_icon="🤖", layout="centered")
st.title("🤖 POOM AI SNTC V6")
st.write("แอปพลิเคชันจัดการและเฉลย Google Form พร้อมระบบแคปเจอร์หน้าจออัจฉริยะ 🇹🇭")

# ==========================================
# ส่วนที่ 1: รับค่าและการตั้งค่าระบบ
# ==========================================
with st.expander("⚙️ การตั้งค่าระบบและเลือกโหมดการทำงาน (คลิกเพื่อซ่อน/แสดง)", expanded=True):
    app_mode = st.selectbox(
        "📌 เลือกโหมดการทำงาน:", 
        [
            "🤖 AI สแกนหาเฉลยข้อสอบ (Gemini / OpenAI)", 
            "📸 เมนูแคปจอออโต้: แคปหน้าจอทั้งหมด 1 ภาพเดี่ยว", 
            "✂️ เมนูแคปจอออโต้: แคปย่อยทีละข้อ (ชัดที่สุด + โหลดแยก/ZIP)"
        ]
    )
    
    if "AI สแกน" in app_mode:
        ai_provider = st.selectbox("🤖 เลือกผู้ให้บริการ AI:", ["Google Gemini", "OpenAI (ChatGPT)"])
        api_key_input = st.text_input(f"🔑 ใส่ API Key ของ {ai_provider}:", type="password")
    else:
        api_key_input = "bypass_key_for_screenshot_mode"
        ai_provider = "None"
        
    form_url = st.text_input("🔗 วางลิงก์ Google Form (เฉพาะฟอร์มที่ไม่ต้องล็อกอิน):")

if st.button("🚀 เริ่มการทำงานของระบบ", type="primary"):
    if not form_url.startswith("http") or (not api_key_input and "AI สแกน" in app_mode):
        st.error("❌ กรุณาตรวจสอบลิงก์ Google Form หรือ API Key ให้ถูกต้อง")
    else:
        st.info("🌐 กำลังเปิดบอทสแกนเนอร์และจัดการหน้าจอ บนระบบคลาวด์...")
        
        ai_client = None
        openai_client = None
        working_model_name = ""
        
        if "AI สแกน" in app_mode:
            try:
                if ai_provider == "Google Gemini":
                    genai.configure(api_key=api_key_input)
                    working_model_name = 'gemini-1.5-flash'
                    try:
                        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        flash_models = [m for m in available_models if 'flash' in m]
                        if flash_models:
                            working_model_name = flash_models[0]
                    except:
                        pass
                    ai_client = genai.GenerativeModel(working_model_name)
                elif ai_provider == "OpenAI (ChatGPT)":
                    openai_client = OpenAI(api_key=api_key_input)
                    working_model_name = 'gpt-4o-mini'
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
            options.add_argument("--window-size=1920,1080")
            
            options.binary_location = "/usr/bin/chromium"
            service = Service("/usr/bin/chromedriver")
            
            driver = webdriver.Chrome(service=service, options=options)
            driver.get(form_url)
            time.sleep(3)

            # --- ระบบทะลวงผ่านหน้าแรกและทุกหน้า (รองรับฟอร์มหลายหน้า) ---
            st.info("🔍 กำลังตรวจสอบหน้าเว็บและทะลวงผ่านหน้ากรอกข้อมูลเพื่อเข้าสู่ข้อสอบ...")
            for step in range(5): # วนลูปกดปุ่ม Next เผื่อฟอร์มมีหลายหน้ากรอกข้อมูล
                try:
                    time.sleep(2)
                    # กรอกข้อมูลช่อง Text ทั่วไปใส่ชื่อ
                    text_inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='email'] | //textarea")
                    for txt in text_inputs:
                        if txt.is_displayed():
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", txt)
                            # ถ้าช่องไหนเป็นตัวเลขหรือรหัส ให้ใส่ '123456' ป้องกันเงื่อนไข Must be a number
                            placeholder_text = txt.get_attribute("aria-describedby") or ""
                            txt.clear()
                            if "number" in txt.get_attribute("outerHTML").lower() or "code" in txt.get_attribute("outerHTML").lower():
                                txt.send_keys("123456")
                            else:
                                txt.send_keys("ทดสอบระบบ")
                            time.sleep(0.5)

                    # เลือกตัวเลือก Radio ตัวแรกสุดของหน้าเสมอถ้ามีบังคับเลือก
                    radio_groups = driver.find_elements(By.XPATH, "//div[@role='radio']")
                    if radio_groups:
                        try:
                            radio_groups[0].click()
                            time.sleep(0.5)
                        except:
                            pass

                    # ค้นหาและคลิกปุ่ม Next / ถัดไป
                    next_buttons = driver.find_elements(By.XPATH, "//span[contains(text(), 'ถัดไป') or contains(text(), 'Next')]/ancestor::div[@role='button']")
                    clicked_next = False
                    for btn in next_buttons:
                        if btn.is_displayed():
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                            time.sleep(1)
                            driver.execute_script("arguments[0].click();", btn)
                            time.sleep(3)
                            clicked_next = True
                            break
                    
                    if not clicked_next:
                        break # ถ้าไม่มีปุ่มถัดไปแสดงว่าเข้าสู่หน้าข้อสอบหลักแล้ว
                except:
                    break

            # --- เวลาปัจจุบันประเทศไทย ---
            thai_time = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
            day_mapping = {'Monday': 'จันทร์', 'Tuesday': 'อังคาร', 'Wednesday': 'พุธ', 'Thursday': 'พฤหัสบดี', 'Friday': 'ศุกร์', 'Saturday': 'เสาร์', 'Sunday': 'อาทิตย์'}
            current_day_th = day_mapping.get(thai_time.strftime("%A"), thai_time.strftime("%A"))
            current_datetime_th = f"วัน{current_day_th} ที่ {thai_time.strftime('%d/%m/%Y')} เวลา {thai_time.strftime('%H:%M:%S')}"

            # ==========================================
            # โหมดที่ 1: แคปหน้าจอทั้งหมด 1 ภาพเดี่ยว
            # ==========================================
            if app_mode == "📸 เมนูแคปจอออโต้: แคปหน้าจอทั้งหมด 1 ภาพเดี่ยว":
                st.info("📸 กำลังประมวลผลจับภาพหน้าจอ Google Form ทั้งหมดในภาพเดียว...")
                
                total_height = driver.execute_script("return document.body.parentNode.scrollHeight")
                driver.set_window_size(1920, total_height + 200)
                time.sleep(2)
                
                full_png = driver.get_screenshot_as_png()
                full_img = Image.open(BytesIO(full_png))
                
                st.success("✅ แคปหน้าจอทั้งหมดสำเร็จเรียบร้อย!")
                st.image(full_img, caption="ภาพหน้าจอ Google Form ทั้งหมด", use_container_width=True)
                
                buffered = BytesIO()
                full_img.save(buffered, format="PNG")
                st.download_button(
                    label="📥 ดาวน์โหลดภาพหน้าจอทั้งหมด (PNG)",
                    data=buffered.getvalue(),
                    file_name="google_form_full_screen.png",
                    mime="image/png"
                )

            # ==========================================
            # โหมดที่ 2: แคปย่อยทีละข้อ (ชัดที่สุด + โหลดแยก/ZIP)
            # ==========================================
            elif app_mode == "✂️ เมนูแคปจอออโต้: แคปย่อยทีละข้อ (ชัดที่สุด + โหลดแยก/ZIP)":
                question_blocks = driver.find_elements(By.XPATH, "//div[@role='listitem']")
                st.success(f"พบบล็อกคำถามทั้งหมด {len(question_blocks)} ข้อ กำลังแคปเจอร์ทีละข้อ...")
                
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for index, block in enumerate(question_blocks):
                        radios = block.find_elements(By.XPATH, ".//div[@role='radio']")
                        text_boxes = block.find_elements(By.XPATH, ".//input[@type='text'] | .//textarea")
                        
                        if not radios and not text_boxes:
                            continue
                            
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", block)
                        time.sleep(0.8)
                        
                        try:
                            block_png = block.screenshot_as_png
                            block_img = Image.open(BytesIO(block_png))
                            
                            heading = block.find_elements(By.XPATH, ".//div[@role='heading']")
                            q_text = heading[0].text if heading else f"ข้อที่ {index+1}"
                            
                            st.markdown("---")
                            st.write(f"📌 **ข้อที่ {index + 1}:** {q_text}")
                            st.image(block_img, caption=f"ภาพข้อที่ {index + 1}", use_container_width=True)
                            
                            img_byte_arr = BytesIO()
                            block_img.save(img_byte_arr, format="PNG")
                            zip_file.writestr(f"question_{index+1}.png", img_byte_arr.getvalue())
                            
                        except Exception as ex:
                            st.warning(f"⚠️ ข้ามข้อที่ {index+1} เนื่องจากเกิดข้อผิดพลาด: {ex}")
                
                st.markdown("---")
                st.success("🎉 แคปเจอร์ภาพแยกรายข้อทั้งหมดเสร็จสมบูรณ์!")
                
                st.download_button(
                    label="📥 ดาวน์โหลดภาพแยกทุกข้อแบบ ZIP",
                    data=zip_buffer.getvalue(),
                    file_name="google_form_all_questions_images.zip",
                    mime="application/zip"
                )

            # ==========================================
            # โหมดที่ 3: AI สแกนหาเฉลยข้อสอบ
            # ==========================================
            elif "AI สแกน" in app_mode:
                model = genai.GenerativeModel(working_model_name) if ai_provider == "Google Gemini" else None
                question_blocks = driver.find_elements(By.XPATH, "//div[@role='listitem']")
                st.success(f"พบบล็อกคำถามทั้งหมด {len(question_blocks)} ข้อ (อ้างอิงเวลา: {current_datetime_th})")
                
                export_text = f"เฉลยข้อสอบจาก POOM AI SNTC V6 ({ai_provider})\nเวลาอ้างอิง: {current_datetime_th}\n" + ("="*40) + "\n\n"
                
                for index, block in enumerate(question_blocks):
                    radios = block.find_elements(By.XPATH, ".//div[@role='radio']")
                    text_boxes = block.find_elements(By.XPATH, ".//input[@type='text'] | .//textarea")
                    
                    if not radios and not text_boxes:
                        continue

                    if index > 0:
                        time.sleep(4)
                        
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
                        prompt = f"""คุณคือผู้เชี่ยวชาญระดับสูง วิเคราะห์ภาพข้อสอบและโจทย์นี้อย่างละเอียด
ข้อมูลอ้างอิงเวลาปัจจุบันประเทศไทย: ขณะนี้คือ {current_datetime_th}
คำถาม: {question_text}
ตัวเลือกที่มี:
{chr(10).join([f'- {c}' for c in choices])}
คำสั่ง: เลือกคำตอบที่ถูกต้องที่สุด ตอบกลับมา "เฉพาะข้อความตัวเลือก" เป๊ะๆ ห้ามมีคำอธิบายเด็ดขาด"""
                    else:
                        st.write(f"✍️ **ข้อ {index + 1} (พิมพ์ตอบ):** {question_text}")
                        prompt = f"""คุณคือผู้เชี่ยวชาญระดับสูง วิเคราะห์ภาพและคำถามข้อสอบนี้อย่างละเอียด
ข้อมูลอ้างอิงเวลาปัจจุบันประเทศไทย: ขณะนี้คือ {current_datetime_th}
คำถาม: {question_text}
คำสั่ง: ตอบคำถามนี้ด้วยข้อความสั้นๆ กระชับ ได้ใจความ และถูกต้องที่สุด ห้ามพิมพ์คำอธิบายหรือคำเกริ่นนำใดๆ ตอบเฉพาะส่วนที่เป็นคำตอบเท่านั้น"""

                    ai_answer = ""
                    for attempt in range(1, 4):
                        try:
                            if ai_provider == "Google Gemini":
                                contents = [prompt, block_img] if block_img else [prompt]
                                response = model.generate_content(contents)
                                ai_answer = response.text.strip()
                            elif ai_provider == "OpenAI (ChatGPT)":
                                import base64
                                buffered = BytesIO()
                                if block_img:
                                    block_img.save(buffered, format="PNG")
                                    img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
                                    messages_content = [
                                        {"type": "text", "text": prompt},
                                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}}
                                    ]
                                else:
                                    messages_content = [{"type": "text", "text": prompt}]
                                    
                                response = openai_client.chat.completions.create(
                                    model=working_model_name,
                                    messages=[{"role": "user", "content": messages_content}],
                                    max_tokens=150
                                )
                                ai_answer = response.choices[0].message.content.strip()

                            if not ai_answer:
                                raise ValueError("AI ตอบค่าว่าง")
                                
                            st.info(f"💡 **POOM AI สรุปคำตอบคือ:** {ai_answer}")
                            if block_img:
                                st.image(block_img, caption="ภาพเฉพาะข้อนี้")
                            break
                        except Exception as ai_err:
                            if "429" in str(ai_err) or "quota" in str(ai_err).lower():
                                st.warning(f"⏳ AI ติดโควตา... กำลังรอ 15 วินาที (ครั้งที่ {attempt}/3)")
                                time.sleep(15)
                            else:
                                st.warning(f"⚠️ พยายามถามใหม่... ({ai_err}) (ครั้งที่ {attempt}/3)")
                                time.sleep(3)
                                
                    if not ai_answer:
                        st.error("❌ AI ไม่สามารถตอบข้อนี้ได้")
                        ai_answer = "[ไม่พบคำตอบ]"

                    export_text += f"ข้อ {index + 1}: {question_text}\nตอบ: {ai_answer}\n\n"
                        
                st.markdown("---")
                st.download_button(
                    label="📥 ดาวน์โหลดไฟล์สรุปคำตอบ (Text)",
                    data=export_text,
                    file_name="poom_ai_sntc_v6_answers.txt",
                    mime="text/plain"
                )
                st.success("🎉 วิเคราะห์และสรุปคำตอบเสร็จสมบูรณ์!")
            
        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาด: {e}")
        finally:
            if driver is not None:
                driver.quit()
