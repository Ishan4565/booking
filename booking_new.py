import streamlit as st
import requests

API_URL = "https://booking-dzz2.onrender.com"

st.set_page_config(page_title="Elite Booking Experience", page_icon="🎭", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #667eea; color: white; }
    .stTextInput>div>div>input { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎭 Elite Booking & AI Review")
st.write("Select a seat to begin your premium experience.")

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
        st.error("Backend is currently unavailable. Please check your Render service.")
except Exception as e:
    st.error(f"Connection Error: {e}")

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

        st.write("---")
        st.write("### 🤖 Complete AI Feedback Section")
        
        exp = st.text_area("Overall Experience *", placeholder="Describe your overall visit...")
        
        st.write("#### Additional Feedback (Optional)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            sound = st.text_input("🔊 Sound Quality", placeholder="How was the audio?")
            seat_height = st.text_input("📏 Seat Height", placeholder="Was the height comfortable?")
            booking_service = st.text_input("🎫 Booking Service", placeholder="How was the booking process?")
            cleanliness = st.text_input("✨ Cleanliness", placeholder="How clean was the venue?")
        
        with col2:
            comfort = st.text_input("💺 Seat Comfort", placeholder="Was the seat cozy?")
            view_quality = st.text_input("👀 View Quality", placeholder="How was the visibility?")
            staff_behavior = st.text_input("👥 Staff Behavior", placeholder="How was the staff?")
            value_for_money = st.text_input("💰 Value for Money", placeholder="Was it worth the price?")

        submitted = st.form_submit_button("Confirm Booking & Submit AI Review")

        if submitted:
            if not u_name or not exp:
                st.warning("Please provide at least your name and overall experience.")
            else:
                with st.spinner("AI is analyzing your feedback..."):
                    book_data = {"user_id": u_id, "user_name": u_name}
                    requests.post(f"{API_URL}/book/{seat['id']}", json=book_data)

                    review_data = {
                        "user_id": u_id,
                        "user_name": u_name,
                        "overall_experience": exp,
                        "sound_quality_review": sound if sound else None,
                        "seat_comfort_review": comfort if comfort else None,
                        "seat_height_review": seat_height if seat_height else None,
                        "view_quality_review": view_quality if view_quality else None,
                        "booking_service_review": booking_service if booking_service else None,
                        "staff_behavior_review": staff_behavior if staff_behavior else None,
                        "cleanliness_review": cleanliness if cleanliness else None,
                        "value_for_money_review": value_for_money if value_for_money else None
                    }
                    rev_res = requests.post(f"{API_URL}/review/{seat['id']}", json=review_data)

                    if rev_res.status_code == 200:
                        st.balloons()
                        st.success(f"Success! Seat {seat['seat_number']} is yours.")
                        
                        analysis = rev_res.json()["review_analysis"]
                        st.write("### 📊 AI Analysis Results:")
                        
                        st.write(f"**Overall Rating:** {analysis['overall_rating'].upper()}")
                        st.write(f"**Average Score:** {analysis['average_score']}")
                        
                        st.write("---")
                        st.write("#### Detailed Sentiment Analysis:")
                        
                        col_result1, col_result2 = st.columns(2)
                        
                        with col_result1:
                            st.metric("Overall Experience", analysis['overall_experience']['sentiment'].title(), 
                                     f"{analysis['overall_experience']['score']}")
                            st.metric("Sound Quality", analysis['sound_quality']['sentiment'].title(), 
                                     f"{analysis['sound_quality']['score']}")
                            st.metric("Seat Comfort", analysis['seat_comfort']['sentiment'].title(), 
                                     f"{analysis['seat_comfort']['score']}")
                            st.metric("Seat Height", analysis['seat_height']['sentiment'].title(), 
                                     f"{analysis['seat_height']['score']}")
                        
                        with col_result2:
                            st.metric("View Quality", analysis['view_quality']['sentiment'].title(), 
                                     f"{analysis['view_quality']['score']}")
                            st.metric("Booking Service", analysis['booking_service']['sentiment'].title(), 
                                     f"{analysis['booking_service']['score']}")
                            st.metric("Staff Behavior", analysis['staff_behavior']['sentiment'].title(), 
                                     f"{analysis['staff_behavior']['score']}")
                            st.metric("Cleanliness", analysis['cleanliness']['sentiment'].title(), 
                                     f"{analysis['cleanliness']['score']}")
                        
                        st.metric("Value for Money", analysis['value_for_money']['sentiment'].title(), 
                                 f"{analysis['value_for_money']['score']}")
                    else:
                        st.error("Booking failed. Please try again.")