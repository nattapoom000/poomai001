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
# ตั้งค่าหน้าเว็บ POOM AI SNTC
# ==========================================
st.set_page_config(page_title="POOM AI SNTC", page_icon="🤖", layout="centered")
st.title("🤖 POOM AI SNTC V1")
st.write("แอปพลิเคชันช่วยตอบ Google Form อัตโนมัติ (รอบคอบพิเศษ รองรับวิเคราะห์รูปภาพและภาษาไทย)")

# ==========================================
# ส่วนที่ 1: รับค่าจากผู้ใช้งาน
# ==========================================
with st.expander("⚙️ การตั้งค่าระบบ (คลิกเพื่อซ่อน/แสดง)", expanded=True):
    api_key_input = st.text_input("🔑 ใส่ Gemini API Key ของคุณ:", type="password")
    form_url = st.text_input("🔗 วางลิงก์ Google Form (เฉพาะฟอร์มที่ไม่ต้องล็อกอิน):")

# ==========================================
# ส่วนที่ 2: เริ่มทำงาน
# ==========================================
if st.button("🚀 ให้ POOM AI เริ่มทำข้อสอบ", type="primary"):
    if not api_key_input:
        st.error("❌ กรุณาใส่ Gemini API Key ก่อนครับ")
    elif not form_url.startswith("http"):
        st.error("❌ กรุณาใส่ลิงก์ Google Form ให้ถูกต้อง")
    else:
        st.info("🌐 กำลังเปิดบอทบน Cloud กรุณารอสักครู่...")
        
        # ตั้งค่า AI และหาโมเดลที่ทำงานได้
        try:
            genai.configure(api_key=api_key_input)
            working_model_name = 'gemini-pro'
            try:
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                for name in available_models:
                    # พยายามหาโมเดล 1.5 flash เพราะอ่านภาพได้เร็วและเก่ง
                    if '1.5' in name and 'flash' in name:
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
            # ตั้งค่า Chrome ล่องหน ให้รองรับภาษาไทยเต็มรูปแบบ
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--lang=th-TH")
            # ตั้งค่าขนาดหน้าต่างเริ่มต้น
            options.add_argument("--window-size=1280,1080")
            
            # ชี้เป้าไปที่ Chrome ของระบบ Cloud
            options.binary_location = "/usr/bin/chromium"
            service = Service("/usr/bin/chromedriver")
            
            driver = webdriver.Chrome(service=service, options=options)
            driver.get(form_url)
            time.sleep(3)

            # ---------------------------------------------------------
            # 1. ระบบจัดการหน้าแรก (ข้ามหน้าอัตโนมัติ)
            # ---------------------------------------------------------
            st.info("🔍 กำลังตรวจสอบโครงสร้างหน้าเว็บ...")
            try:
                # หาช่องกรอกข้อความ แล้วใส่คำว่า "ทดสอบ"
                text_inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='email'] | //textarea")
                for txt in text_inputs:
                    if txt.is_displayed():
                        txt.send_keys("ทดสอบ")
                
                # หาปุ่ม ถัดไป / Next แล้วกด
                next_buttons = driver.find_elements(By.XPATH, "//div[@role='button']//span[contains(text(), 'ถัดไป') or contains(text(), 'Next')]/ancestor::div[@role='button']")
                for btn in next_buttons:
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                        time.sleep(1)
                        btn.click()
                        time.sleep(3) # รอหน้าใหม่โหลด
                        st.success("➡️ บอทข้ามหน้าแรกมายังหน้าข้อสอบสำเร็จ!")
                        break
            except Exception:
                pass 
            
            # ---------------------------------------------------------
            # 2. แคปหน้าจอแบบ Full-Page (เต็มหน้าเว็บ)
            # ---------------------------------------------------------
            st.markdown("### 📸 ภาพรวมของหน้าเว็บทั้งหมด ณ ปัจจุบัน")
            try:
                # คำนวณความยาวทั้งหมดของหน้าเว็บ
                total_width = driver.execute_script("return document.body.parentNode.scrollWidth")
                total_height = driver.execute_script("return document.body.parentNode.scrollHeight")
                
                # ขยายหน้าต่างให้เท่ากับความยาวหน้าเว็บ เพื่อถ่ายรอบเดียวจบ
                driver.set_window_size(total_width, total_height)
                time.sleep(1) # รอเรนเดอร์ภาพใหม่
                screenshot = driver.get_screenshot_as_png()
                st.image(screenshot, caption="ภาพแคปเจอร์แบบเต็มหน้า (Full Page)", use_container_width=True)
            except Exception as img_e:
                st.warning(f"ถ่ายภาพเต็มหน้าไม่สำเร็จ: {img_e}")

            # ---------------------------------------------------------
            # 3. เริ่มกวาดข้อสอบ
            # ---------------------------------------------------------
            question_blocks = driver.find_elements(By.XPATH, "//div[@role='listitem']")
            st.success(f"พบบล็อกคำถามทั้งหมด {len(question_blocks)} ข้อ")
            
            export_text = "เฉลยข้อสอบจาก POOM AI SNTC\n" + ("="*40) + "\n\n"
            
            for index, block in enumerate(question_blocks):
                # หน่วงเวลา 3 วินาที ป้องกันลิมิตของ API
                if index > 0:
                    time.sleep(3)
                    
                heading_elements = block.find_elements(By.XPATH, ".//div[@role='heading']")
                question_text = heading_elements[0].text if heading_elements else ""
                
                # ค้นหารูปภาพในข้อนี้
                img_elements = block.find_elements(By.XPATH, ".//img")
                img_content = None
                if img_elements:
                    try:
                        # เลื่อนจอไปที่รูปเพื่อให้โหลดเสร็จก่อนแคปเฉพาะรูป
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", img_elements[0])
                        time.sleep(0.5)
                        img_png = img_elements[0].screenshot_as_png
                        img_content = Image.open(BytesIO(img_png))
                    except:
                        pass
                
                radio_buttons = block.find_elements(By.XPATH, ".//div[@role='radio']")
                if not radio_buttons: continue
                choices = [r.get_attribute("data-value") for r in radio_buttons if r.get_attribute("data-value")]
                
                display_q = question_text if question_text else "[ข้อสอบเป็นรูปภาพ ไม่มีตัวหนังสือ]"
                
                if choices:
                    st.markdown("---")
                    st.markdown(f"**📝 ข้อ {index + 1}:** {display_q}")
                    
                    # ---------------------------------------------------------
                    # ตั้งค่า Prompt แบบเข้มงวดสุดๆ ป้องกัน AI มโน
                    # ---------------------------------------------------------
                    strict_prompt = f"""คุณคือผู้เชี่ยวชาญระดับสูงที่มีความรอบคอบและแม่นยำขั้นสูงสุด
กรุณาอ่านคำถามและวิเคราะห์รูปภาพประกอบอย่างละเอียด:
1. ตรวจสอบสัญลักษณ์ทางคณิตศาสตร์ ตัวเลข ภาษาไทย และภาษาอังกฤษทุกตัวอักษรอย่างระมัดระวัง ห้ามอ่านผิดหรือข้ามรายละเอียด
2. ห้ามจินตนาการ มโน หรือเพิ่มข้อมูล/ตัวเลข/สัญลักษณ์ที่ไม่มีอยู่จริงในภาพเด็ดขาด
3. หากเป็นสมการคณิตศาสตร์ ให้คำนวณตามหลักการทางคณิตศาสตร์อย่างถูกต้องแม่นยำ
4. เปรียบเทียบผลลัพธ์ที่คุณวิเคราะห์ได้ กับตัวเลือกที่มีให้ตรงกันเป๊ะๆ

คำถาม: {display_q}
ตัวเลือก:
{chr(10).join([f'- {c}' for c in choices])}

เมื่อวิเคราะห์เสร็จแล้ว ให้ตอบกลับมา "เฉพาะข้อความของตัวเลือกที่ถูกต้องที่สุดเพียง 1 ข้อเท่านั้น" ห้ามพิมพ์คำอธิบายหรือข้อความอื่นเจือปนเด็ดขาด"""
                    
                    contents_to_send = []
                    if img_content:
                        st.image(img_content, caption="ภาพประกอบโจทย์ข้อนี้")
                        contents_to_send = [strict_prompt, img_content]
                    else:
                        contents_to_send = [strict_prompt]
                    
                    # ถาม AI พร้อมระบบ Retry (ลองถามใหม่ถ้าติดลิมิต)
                    ai_answer = ""
                    for attempt in range(1, 4):
                        try:
                            response = model.generate_content(contents_to_send)
                            ai_answer = response.text.strip()
                            st.info(f"💡 **POOM AI ตอบ:** {ai_answer}")
                            break
                        except Exception as ai_err:
                            err_str = str(ai_err).lower()
                            if "429" in err_str or "quota" in err_str or "exhausted" in err_str:
                                st.warning(f"⏳ AI ทำงานเร็วเกินไป... รอพัก 10 วินาที (ครั้งที่ {attempt}/3)")
                                time.sleep(10)
                            else:
                                st.warning(f"⚠️ AI ตอบไม่ได้: {ai_err}")
                                break
                    
                    # บันทึกคำตอบและสั่งบอทให้กดคลิกตัวเลือกในหน้าเว็บ
                    if ai_answer:
                        export_text += f"ข้อ {index + 1}: {display_q}\n"
                        if img_content:
                            export_text += "[มีภาพประกอบในโจทย์]\n"
                        export_text += f"POOM AI ตอบ: {ai_answer}\n"
                        export_text += "-"*30 + "\n\n"
                        
                        for radio in radio_buttons:
                            # เทียบคำตอบ AI กับตัวเลือก ถ้าตรงกันให้คลิก
                            if radio.get_attribute("data-value").strip() == ai_answer:
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", radio)
                                time.sleep(0.5)
                                radio.click()
                                break
            
            # ---------------------------------------------------------
            # 4. ปุ่มดาวน์โหลดไฟล์เฉลย
            # ---------------------------------------------------------
            st.markdown("---")
            st.markdown("### 💾 บันทึกข้อมูลทั้งหมด")
            st.download_button(
                label="📥 ดาวน์โหลดเฉลยเป็นไฟล์ Text",
                data=export_text,
                file_name="poom_ai_sntc_answers.txt",
                mime="text/plain"
            )
            
            st.success("🎉 บอท POOM AI SNTC วิเคราะห์และตอบคำถามเสร็จสมบูรณ์!")
            
        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาดในระบบ: {e}")
        finally:
            if driver is not None:
                driver.quit()
