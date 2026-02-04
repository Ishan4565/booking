import streamlit as st
import requests

# 1. YOUR CONFIG
API_URL = "https://booking-dzz2.onrender.com"

st.set_page_config(page_title="Elite Booking Experience", page_icon="🎭", layout="centered")

# 2. STYLE
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #667eea; color: white; }
    .stTextInput>div>div>input { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎭 Elite Booking & AI Review")
st.write("Select a seat to begin your premium experience.")

# 3. FETCH SEATS
try:
    response = requests.get(f"{API_URL}/seats")
    if response.status_code == 200:
        seats_data = response.json()["seats"]
        st.subheader("Available Seating")
        cols = st.columns(5)
        for i, seat in enumerate(seats_data):
            with cols[i % 5]:
                seat_label = f"💺 {seat['seat_number']}"
                is_available = seat['status'] == 'available'
                if st.button(seat_label, key=f"seat_{seat['id']}", disabled=not is_available):
                    st.session_state.selected_seat = seat
                    st.session_state.booking_step = True
    else:
        st.error("Backend is sleeping. Please wait for Render to wake up.")
except Exception as e:
    st.error(f"Connection Error: {e}")

# 4. THE FORM
if st.session_state.get("booking_step"):
    seat = st.session_state.selected_seat
    st.divider()
    st.subheader(f"Confirming Seat: {seat['seat_number']}")

    with st.form("universal_booking_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            u_name = st.text_input("Name", placeholder="Enter your name")
        with col_b:
            u_id = st.number_input("Customer ID", value=101)

        st.write("### 🤖 AI Feedback Section")
        exp = st.text_area("Overall Experience *", placeholder="Describe your overall visit...")
        
        col1, col2 = st.columns(2)
        with col1:
            sound = st.text_input("🔊 Sound Quality")
            seat_height = st.text_input("📏 Seat Height")
            booking_service = st.text_input("🎫 Booking Service")
            cleanliness = st.text_input("✨ Cleanliness")
        with col2:
            comfort = st.text_input("💺 Seat Comfort")
            view_quality = st.text_input("👀 View Quality")
            staff_behavior = st.text_input("👥 Staff Behavior")
            value_for_money = st.text_input("💰 Value for Money")

        submitted = st.form_submit_button("Confirm Booking & AI Review")

        if submitted:
            if not u_name or not exp:
                st.warning("Please provide at least your name and overall experience.")
            else:
                with st.spinner("AI is analyzing..."):
                    # This sends data to the API (the backend)
                    requests.post(f"{API_URL}/book/{seat['id']}", json={"user_id": u_id, "user_name": u_name})
                    
                    review_data = {
                        "user_id": u_id, "user_name": u_name, "overall_experience": exp,
                        "sound_quality_review": sound, "seat_comfort_review": comfort,
                        "seat_height_review": seat_height, "view_quality_review": view_quality,
                        "booking_service_review": booking_service, "staff_behavior_review": staff_behavior,
                        "cleanliness_review": cleanliness, "value_for_money_review": value_for_money
                    }
                    rev_res = requests.post(f"{API_URL}/review/{seat['id']}", json=review_data)

                    if rev_res.status_code == 200:
                        st.balloons()
                        analysis = rev_res.json()["review_analysis"]
                        st.write("### 📊 AI Results:")
                        st.json(analysis)
                    else:
                        st.error("Booking failed.")
