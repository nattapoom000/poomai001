import streamlit as st
import time
import datetime
import base64
import zipfile
from io import BytesIO
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import google.generativeai as genai
from openai import OpenAI

# ==========================================
# ตั้งค่าหน้าเว็บ POOM AI SNTC V6.5
# ==========================================
st.set_page_config(page_title="POOM AI SNTC V6.5", page_icon="🤖", layout="centered")
st.title("🤖 POOM AI SNTC V6.5")
st.write("ระบบเฉลยและแคปจอ Google Form (ระบบ Auto-Fallback + ปรับแต่งชื่อโมเดลอิสระ 🇹🇭)")

# ==========================================
# ส่วนที่ 1: รับค่าและการตั้งค่าระบบ
# ==========================================
with st.expander("⚙️ การตั้งค่าระบบและ API Keys (คลิกเพื่อซ่อน/แสดง)", expanded=True):
    app_mode = st.selectbox(
        "📌 เลือกโหมดการทำงาน:", 
        [
            "🤖 AI สแกนหาเฉลยข้อสอบ (Auto-Fallback สลับค่ายอัตโนมัติ)", 
            "📸 แคปจอออโต้: แคปหน้าจอรวมทุกหน้า (ต่อกันเป็น 1 ภาพยาว)", 
            "📸 แคปจอออโต้: แคปแยก 1 หน้าต่อ 1 ภาพ (มีปุ่มโหลดแยกทีละภาพ)", 
            "✂️ แคปจอออโต้: แคปย่อยทีละข้อ (มีปุ่มโหลดแยกทีละข้อ)"
        ]
    )
    
    if "AI สแกน" in app_mode:
        st.subheader("🔑 ตั้งค่า API Keys (ใส่เฉพาะอันที่มี ระบบจะสลับให้อัตโนมัติ)")
        
        gemini_key = st.text_input("1. Google Gemini API Key (ฟรี):", type="password")
        
        st.markdown("---")
        groq_key = st.text_input("2. Groq API Key (ฟรี / เร็วมาก):", type="password", help="สมัครฟรีที่ console.groq.com")
        # เพิ่มช่องกรอกชื่อโมเดลของ Groq ให้เปลี่ยนได้อิสระ
        groq_model = st.text_input("📌 ชื่อโมเดล Groq Vision (อัปเดตได้อิสระ):", value="llama-3.2-90b-vision-specdec", help="ดูชื่อโมเดลล่าสุดที่ console.groq.com/docs/models")
        
        st.markdown("---")
        openrouter_key = st.text_input("3. OpenRouter API Key (ฟรี):", type="password", help="สมัครฟรีที่ openrouter.ai")
        # เพิ่มช่องกรอกชื่อโมเดลของ OpenRouter
        openrouter_model = st.text_input("📌 ชื่อโมเดล OpenRouter:", value="google/gemini-2.0-flash-exp:free")
        
        st.markdown("---")
        openai_key = st.text_input("4. OpenAI API Key (แบบเติมเงิน - ถ้ามี):", type="password")
    else:
        gemini_key = groq_key = groq_model = openrouter_key = openrouter_model = openai_key = "bypass"
        
    form_url = st.text_input("🔗 วางลิงก์ Google Form (เฉพาะฟอร์มที่ไม่ต้องล็อกอิน):")

# ==========================================
# ฟังก์ชันระบบ AI Auto-Fallback
# ==========================================
def ask_ai_with_fallback(prompt, block_img, current_datetime_th, gemini_key, groq_key, groq_model, openrouter_key, openrouter_model, openai_key):
    """ฟังก์ชันยิงคำถามหา AI ตามลำดับ หากค่ายไหนติดลิมิตจะสลับไปค่ายถัดไปทันที"""
    
    # 1. ลองใช้ Google Gemini
    if gemini_key and gemini_key != "bypass":
        try:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            contents = [prompt, block_img] if block_img else [prompt]
            response = model.generate_content(contents)
            if response.text.strip():
                return response.text.strip(), "Google Gemini 🟢"
        except Exception as e:
            st.warning(f"⚠️ Gemini ขัดข้อง สลับไปใช้ AI สำรอง... ({e})")

    # แปลงภาพเป็น Base64
    img_base64 = None
    if block_img:
        buffered = BytesIO()
        block_img.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    # 2. ลองใช้ Groq (ใช้ชื่อโมเดลจากหน้าเว็บ)
    if groq_key and groq_key != "bypass":
        try:
            client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
            messages_content = [{"type": "text", "text": prompt}]
            if img_base64:
                messages_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}})
            
            response = client.chat.completions.create(
                model=groq_model.strip(), # ใช้ค่าจากกล่องข้อความ
                messages=[{"role": "user", "content": messages_content}],
                max_tokens=150
            )
            ans = response.choices[0].message.content.strip()
            if ans:
                return ans, f"Groq ({groq_model}) ⚡"
        except Exception as e:
            st.warning(f"⚠️ Groq ขัดข้อง สลับไปใช้ AI สำรอง... ({e})")

    # 3. ลองใช้ OpenRouter (ใช้ชื่อโมเดลจากหน้าเว็บ)
    if openrouter_key and openrouter_key != "bypass":
        try:
            client = OpenAI(api_key=openrouter_key, base_url="https://openrouter.ai/api/v1")
            messages_content = [{"type": "text", "text": prompt}]
            if img_base64:
                messages_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}})
            
            response = client.chat.completions.create(
                model=openrouter_model.strip(), # ใช้ค่าจากกล่องข้อความ
                messages=[{"role": "user", "content": messages_content}],
                max_tokens=150
            )
            ans = response.choices[0].message.content.strip()
            if ans:
                return ans, f"OpenRouter ({openrouter_model}) 🔵"
        except Exception as e:
            st.warning(f"⚠️ OpenRouter ขัดข้อง... ({e})")

    # 4. ลองใช้ OpenAI ChatGPT
    if openai_key and openai_key != "bypass":
        try:
            client = OpenAI(api_key=openai_key)
            messages_content = [{"type": "text", "text": prompt}]
            if img_base64:
                messages_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}})
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": messages_content}],
                max_tokens=150
            )
            ans = response.choices[0].message.content.strip()
            if ans:
                return ans, "OpenAI (GPT-4o mini) 🤖"
        except Exception as e:
            st.warning(f"⚠️ OpenAI ขัดข้อง... ({e})")

    return "[ไม่พบคำตอบ / AI ทุกค่ายติดลิมิตหรือโมเดลมีปัญหา]", "Error ❌"

# ==========================================
# ส่วนที่ 2: เริ่มการทำงานหลัก
# ==========================================
if st.button("🚀 เริ่มสแกนและประมวลผล", type="primary"):
    has_keys = any([gemini_key, groq_key, openrouter_key, openai_key])
    if not form_url.startswith("http") or (not has_keys and "AI สแกน" in app_mode):
        st.error("❌ กรุณาตรวจสอบลิงก์ Google Form หรือใส่ API Key อย่างน้อย 1 ค่าย")
    else:
        st.info("🌐 กำลังเปิดบอทสแกนเนอร์บนระบบ Cloud...")
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

            thai_time = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
            current_datetime_th = f"{thai_time.strftime('%d/%m/%Y')} เวลา {thai_time.strftime('%H:%M:%S')}"

            full_page_images = []
            zip_buffer = BytesIO()
            zip_file = zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) if "แคปย่อย" in app_mode or "แคปแยก" in app_mode else None
            export_text = f"เฉลยข้อสอบ POOM AI (Auto-Fallback)\nเวลาอ้างอิง: {current_datetime_th}\n" + ("="*40) + "\n\n"
            
            global_q_index = 1

            # ========================================================
            # ระบบประมวลผลทีละหน้า
            # ========================================================
            for page_num in range(1, 15): 
                st.markdown(f"### 📄 กำลังประมวลผลหน้าที่ {page_num}")
                time.sleep(2)

                # ----------------------------------------------------
                # โหมดแคปจอต่างๆ
                # ----------------------------------------------------
                if "ต่อกันเป็น 1 ภาพยาว" in app_mode or "แคปแยก 1 หน้า" in app_mode:
                    total_height = driver.execute_script("return document.body.parentNode.scrollHeight")
                    driver.set_window_size(1920, total_height + 200)
                    time.sleep(1.5)
                    full_png = driver.get_screenshot_as_png()
                    img = Image.open(BytesIO(full_png))
                    
                    if "ต่อกันเป็น 1 ภาพยาว" in app_mode:
                        full_page_images.append(img)
                        st.image(img, caption=f"ภาพหน้าจอหน้าที่ {page_num}", use_container_width=True)
                    elif "แคปแยก 1 หน้า" in app_mode:
                        img_byte_arr = BytesIO()
                        img.save(img_byte_arr, format="PNG")
                        zip_file.writestr(f"Page_{page_num}.png", img_byte_arr.getvalue())
                        
                        st.image(img, caption=f"ภาพหน้าจอหน้าที่ {page_num}", use_container_width=True)
                        st.download_button(
                            label=f"📥 โหลดภาพหน้าที่ {page_num}",
                            data=img_byte_arr.getvalue(),
                            file_name=f"Page_{page_num}.png",
                            mime="image/png",
                            key=f"dl_page_{page_num}"
                        )

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
                            st.download_button(
                                label=f"📥 โหลดรูปข้อที่ {global_q_index}",
                                data=img_byte_arr.getvalue(),
                                file_name=f"Question_{global_q_index}.png",
                                mime="image/png",
                                key=f"dl_q_{global_q_index}"
                            )
                            global_q_index += 1
                        except: pass

                # ----------------------------------------------------
                # โหมด AI สแกนเฉลยข้อสอบ
                # ----------------------------------------------------
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
                            prompt = f"""You are an academic expert. Analyze this question (Thai/English).
Question: {question_text}
Options: {chr(10).join([f'- {c}' for c in choices])}
Select the single most correct option. Reply ONLY with the exact text of the correct option."""
                        else:
                            st.write(f"✍️ **ข้อ {global_q_index} (พิมพ์ตอบ):** {question_text}")
                            prompt = f"""You are an academic expert. Answer this question correctly and concisely. Reply ONLY with the correct answer."""

                        # โยนพารามิเตอร์ชื่อโมเดลเข้าไปในฟังก์ชัน Fallback
                        ai_answer, provider_used = ask_ai_with_fallback(
                            prompt, block_img, current_datetime_th, 
                            gemini_key, groq_key, groq_model, openrouter_key, openrouter_model, openai_key
                        )
                        
                        st.info(f"💡 **คำตอบคือ:** {ai_answer} *(ประมวลผลโดย: {provider_used})*")
                        export_text += f"ข้อ {global_q_index}: {question_text}\nตอบ: {ai_answer}\n\n"
                        global_q_index += 1

                # ----------------------------------------------------
                # ระบบทะลวงไปหน้าถัดไป
                # ----------------------------------------------------
                next_buttons = driver.find_elements(By.XPATH, "//span[contains(text(), 'ถัดไป') or contains(text(), 'Next') or contains(text(), 'next')]/ancestor::div[@role='button']")
                visible_next = [b for b in next_buttons if b.is_displayed()]
                
                if not visible_next:
                    st.success("🏁 พบปุ่ม Submit / หน้าสุดท้ายของฟอร์มแล้ว สิ้นสุดการประมวลผล")
                    break

                st.warning("➡️ พบปุ่มถัดไป กำลังกรอกข้อมูลดัมมี่ (123456789) เพื่อทะลวงไปหน้าต่อไป...")
                
                for txt in driver.find_elements(By.XPATH, "//input[@type='text' or @type='email' or @type='number'] | //textarea"):
                    if txt.is_displayed():
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", txt)
                        try: txt.clear(); txt.send_keys("123456789")
                        except: pass
                
                for item in driver.find_elements(By.XPATH, "//div[@role='listitem']"):
                    try: item.find_elements(By.XPATH, ".//div[@role='radio']")[0].click()
                    except: pass
                    try: item.find_elements(By.XPATH, ".//div[@role='checkbox']")[0].click()
                    except: pass

                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", visible_next[0])
                time.sleep(1)
                driver.execute_script("arguments[0].click();", visible_next[0])
                time.sleep(3) 

            # ========================================================
            # จัดเตรียมไฟล์สำหรับดาวน์โหลด
            # ========================================================
            st.markdown("---")
            if "ต่อกันเป็น 1 ภาพยาว" in app_mode:
                if len(full_page_images) == 1:
                    buffered = BytesIO()
                    full_page_images[0].save(buffered, format="PNG")
                else:
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

            elif "แคปแยก" in app_mode or "แคปย่อย" in app_mode:
                if zip_file: zip_file.close()
                filename = "google_form_pages.zip" if "แคปแยก 1 หน้า" in app_mode else "google_form_questions.zip"
                st.download_button("📦 ดาวน์โหลดรวมทุกภาพเป็นไฟล์ ZIP", zip_buffer.getvalue(), filename, "application/zip")

            elif "AI สแกน" in app_mode:
                st.download_button("📥 ดาวน์โหลดไฟล์สรุปคำตอบ (Text)", export_text, "poom_ai_answers.txt", "text/plain")
                
            st.balloons()
            
        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาด: {e}")
        finally:
            if driver is not None:
                driver.quit()
