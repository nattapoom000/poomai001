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
# ตั้งค่าหน้าเว็บ POOM AI SNTC V6.1
# ==========================================
st.set_page_config(page_title="POOM AI SNTC V6.1", page_icon="🤖", layout="centered")
st.title("🤖 POOM AI SNTC V6.1")
st.write("แอปพลิเคชันเฉลยข้อสอบและแคปจอ Google Form (รองรับหลายหน้า/ประมวลผลก่อนกรอก)")

# ==========================================
# ส่วนที่ 1: รับค่าจากผู้ใช้งาน
# ==========================================
with st.expander("⚙️ การตั้งค่าระบบ (คลิกเพื่อซ่อน/แสดง)", expanded=True):
    app_mode = st.selectbox(
        "📌 เลือกโหมดการทำงาน:", 
        [
            "🤖 AI สแกนหาเฉลยข้อสอบ (Gemini / OpenAI)", 
            "📸 แคปจอออโต้: แคปหน้าจอรวมทุกหน้า (ต่อกันเป็น 1 ภาพยาว)", 
            "✂️ แคปจอออโต้: แคปย่อยทีละข้อ (แยกข้อ + โหลดไฟล์ ZIP)"
        ]
    )
    
    if "AI สแกน" in app_mode:
        ai_provider = st.selectbox("🤖 เลือกผู้ให้บริการ AI:", ["Google Gemini", "OpenAI (ChatGPT)"])
        api_key_input = st.text_input(f"🔑 ใส่ API Key ของ {ai_provider}:", type="password")
    else:
        api_key_input = "bypass_key_for_screenshot_mode"
        ai_provider = "None"
        
    form_url = st.text_input("🔗 วางลิงก์ Google Form (เฉพาะฟอร์มที่ไม่ต้องล็อกอิน):")

if st.button("🚀 เริ่มสแกนและประมวลผล", type="primary"):
    if not form_url.startswith("http") or (not api_key_input and "AI สแกน" in app_mode):
        st.error("❌ กรุณาตรวจสอบลิงก์ Google Form หรือ API Key ให้ถูกต้อง")
    else:
        st.info("🌐 กำลังเชื่อมต่อเบราว์เซอร์บนระบบ Cloud...")
        
        ai_client, openai_client, working_model_name = None, None, ""
        
        if "AI สแกน" in app_mode:
            try:
                if ai_provider == "Google Gemini":
                    genai.configure(api_key=api_key_input)
                    working_model_name = 'gemini-1.5-flash'
                    try:
                        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        if any('flash' in m for m in available_models):
                            working_model_name = [m for m in available_models if 'flash' in m][0]
                    except: pass
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
            options.add_argument("--lang=th-TH,en-US")
            options.add_argument("--window-size=1920,1080")
            
            options.binary_location = "/usr/bin/chromium"
            service = Service("/usr/bin/chromedriver")
            
            driver = webdriver.Chrome(service=service, options=options)
            driver.get(form_url)
            time.sleep(3)

            # --- เวลาปัจจุบัน ---
            thai_time = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
            current_datetime_th = f"{thai_time.strftime('%d/%m/%Y')} เวลา {thai_time.strftime('%H:%M:%S')}"

            # --- ตัวแปรเก็บข้อมูลข้ามหน้า ---
            full_page_images = []
            zip_buffer = BytesIO()
            zip_file = zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) if "แคปย่อย" in app_mode else None
            export_text = f"เฉลยข้อสอบ POOM AI ({ai_provider})\nเวลาอ้างอิง: {current_datetime_th}\n" + ("="*40) + "\n\n"
            
            global_q_index = 1

            # ========================================================
            # ระบบประมวลผลทีละหน้า (แคปก่อนกรอก -> กรอกจำลอง -> กด Next)
            # ========================================================
            for page_num in range(1, 15): # รองรับสูงสุด 15 หน้า
                st.markdown(f"### 📄 กำลังประมวลผลหน้าที่ {page_num}")
                time.sleep(2) # รอหน้าเว็บโหลดเสร็จสมบูรณ์

                # ----------------------------------------------------
                # ส่วนที่ 1: แคปจอ หรือ AI สแกน (ทำทันทีก่อนกรอกข้อมูลใดๆ)
                # ----------------------------------------------------
                if "1 ภาพเดี่ยว" in app_mode:
                    total_height = driver.execute_script("return document.body.parentNode.scrollHeight")
                    driver.set_window_size(1920, total_height + 200)
                    time.sleep(1.5)
                    full_png = driver.get_screenshot_as_png()
                    img = Image.open(BytesIO(full_png))
                    full_page_images.append(img)
                    st.image(img, caption=f"ภาพหน้าจอหน้าที่ {page_num}", use_container_width=True)

                elif "แคปย่อย" in app_mode:
                    blocks = driver.find_elements(By.XPATH, "//div[@role='listitem']")
                    for block in blocks:
                        if not block.find_elements(By.XPATH, ".//div[@role='radio'] | .//input[@type='text'] | .//textarea"):
                            continue
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", block)
                        time.sleep(0.5)
                        try:
                            img = Image.open(BytesIO(block.screenshot_as_png))
                            img_byte_arr = BytesIO()
                            img.save(img_byte_arr, format="PNG")
                            zip_file.writestr(f"Page{page_num}_Q{global_q_index}.png", img_byte_arr.getvalue())
                            st.image(img, caption=f"ข้อที่ {global_q_index}", use_container_width=True)
                            global_q_index += 1
                        except: pass

                elif "AI สแกน" in app_mode:
                    blocks = driver.find_elements(By.XPATH, "//div[@role='listitem']")
                    for block in blocks:
                        radios = block.find_elements(By.XPATH, ".//div[@role='radio']")
                        text_boxes = block.find_elements(By.XPATH, ".//input[@type='text'] | .//textarea")
                        if not radios and not text_boxes: continue

                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", block)
                        time.sleep(0.5)
                        
                        try: block_img = Image.open(BytesIO(block.screenshot_as_png))
                        except: block_img = None
                        
                        heading = block.find_elements(By.XPATH, ".//div[@role='heading']")
                        question_text = heading[0].text if heading else f"[Question {global_q_index}]"
                        
                        st.markdown("---")
                        if radios:
                            st.write(f"📝 **ข้อ {global_q_index} (ตัวเลือก):** {question_text}")
                            choices = [r.get_attribute("data-value") for r in radios if r.get_attribute("data-value")]
                            prompt = f"""You are a top-tier academic expert. Analyze this question (Thai/English).
Time: {current_datetime_th}
Question: {question_text}
Options: {chr(10).join([f'- {c}' for c in choices])}
Select the single most correct option. Reply ONLY with the exact text of the correct option."""
                        else:
                            st.write(f"✍️ **ข้อ {global_q_index} (พิมพ์ตอบ):** {question_text}")
                            prompt = f"""You are a top-tier academic expert. Answer this question correctly and concisely. Reply ONLY with the correct answer."""

                        ai_answer = ""
                        for attempt in range(1, 4):
                            try:
                                if ai_provider == "Google Gemini":
                                    contents = [prompt, block_img] if block_img else [prompt]
                                    response = ai_client.generate_content(contents)
                                    ai_answer = response.text.strip()
                                elif ai_provider == "OpenAI (ChatGPT)":
                                    import base64
                                    messages_content = [{"type": "text", "text": prompt}]
                                    if block_img:
                                        buffered = BytesIO()
                                        block_img.save(buffered, format="PNG")
                                        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
                                        messages_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}})
                                    response = openai_client.chat.completions.create(
                                        model=working_model_name, messages=[{"role": "user", "content": messages_content}], max_tokens=150
                                    )
                                    ai_answer = response.choices[0].message.content.strip()
                                
                                if ai_answer:
                                    st.info(f"💡 **คำตอบคือ:** {ai_answer}")
                                    break
                            except Exception as ai_err:
                                if "429" in str(ai_err): time.sleep(15)
                                else: time.sleep(3)
                        
                        if not ai_answer: ai_answer = "[ไม่พบคำตอบ / No answer]"
                        export_text += f"ข้อ {global_q_index}: {question_text}\nตอบ: {ai_answer}\n\n"
                        global_q_index += 1

                # ----------------------------------------------------
                # ส่วนที่ 2: ตรวจสอบปุ่ม Next ถ้ามีให้กรอกข้อมูลแล้วไปต่อ
                # ----------------------------------------------------
                next_buttons = driver.find_elements(By.XPATH, "//span[contains(text(), 'ถัดไป') or contains(text(), 'Next') or contains(text(), 'next')]/ancestor::div[@role='button']")
                visible_next = [b for b in next_buttons if b.is_displayed()]
                
                if not visible_next:
                    st.success("🏁 พบปุ่ม Submit / หน้าสุดท้ายของฟอร์มแล้ว สิ้นสุดการประมวลผล")
                    break # หลุดออกจากลูปเมื่อถึงหน้าสุดท้าย

                st.warning("➡️ พบปุ่มถัดไป กำลังกรอกข้อมูลดัมมี่ (123456789) เพื่อทะลวงไปหน้าต่อไป...")
                
                # กรอก 123456789 ในทุกช่องข้อความ
                for txt in driver.find_elements(By.XPATH, "//input[@type='text' or @type='email' or @type='number'] | //textarea"):
                    if txt.is_displayed():
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", txt)
                        try: txt.clear(); txt.send_keys("123456789")
                        except: pass
                
                # คลิก Radio / Checkbox อันแรกของทุกข้อ
                for item in driver.find_elements(By.XPATH, "//div[@role='listitem']"):
                    try: item.find_elements(By.XPATH, ".//div[@role='radio']")[0].click()
                    except: pass
                    try: item.find_elements(By.XPATH, ".//div[@role='checkbox']")[0].click()
                    except: pass

                # กด Next
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", visible_next[0])
                time.sleep(1)
                driver.execute_script("arguments[0].click();", visible_next[0])
                time.sleep(3) # รอหน้าใหม่โหลด

            # ========================================================
            # จัดเตรียมไฟล์สำหรับดาวน์โหลด
            # ========================================================
            st.markdown("---")
            if "1 ภาพเดี่ยว" in app_mode:
                if len(full_page_images) == 1:
                    buffered = BytesIO()
                    full_page_images[0].save(buffered, format="PNG")
                else:
                    # นำภาพทุกหน้ามาต่อกันเป็นแนวตั้ง 1 ภาพยาว
                    total_width = max(img.width for img in full_page_images)
                    total_height = sum(img.height for img in full_page_images)
                    stitched_img = Image.new('RGB', (total_width, total_height))
                    y_offset = 0
                    for img in full_page_images:
                        stitched_img.paste(img, (0, y_offset))
                        y_offset += img.height
                    buffered = BytesIO()
                    stitched_img.save(buffered, format="PNG")
                    st.success("✅ นำภาพทุกหน้ามาต่อกันเสร็จสมบูรณ์!")
                    
                st.download_button("📥 ดาวน์โหลดภาพหน้าจอ (PNG ยาวรวมทุกหน้า)", buffered.getvalue(), "google_form_full.png", "image/png")

            elif "แคปย่อย" in app_mode:
                if zip_file: zip_file.close()
                st.download_button("📥 ดาวน์โหลดภาพแยกทุกข้อแบบ ZIP", zip_buffer.getvalue(), "google_form_questions.zip", "application/zip")

            elif "AI สแกน" in app_mode:
                st.download_button("📥 ดาวน์โหลดไฟล์สรุปคำตอบ (Text)", export_text, "poom_ai_answers.txt", "text/plain")
                
            st.balloons()
            
        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาด: {e}")
        finally:
            if driver is not None:
                driver.quit()
