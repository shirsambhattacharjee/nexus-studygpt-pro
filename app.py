
    with tab2:
        st.markdown("### 🎯 Dynamic Diagnostic Assessment Module")
        raw_json_str = data.get("quiz", "{}")
        parsed_quiz = None
        
        try:
            clean_str = re.sub(r"^```(json)?", "", raw_json_str.strip())
            clean_str = re.sub(r"```$", "", clean_str).strip()
            parsed_quiz = json.loads(clean_str)
        except Exception:
            pass

        if parsed_quiz and "questions" in parsed_quiz and parsed_quiz["questions"]:
            questions_list = parsed_quiz["questions"]
            selections = []
            
            for i, q_item in enumerate(questions_list):
                st.markdown(f"""
                <div class="glass-card" style="margin-bottom: 18px; border-left: 4px solid #6366f1;">
                    <p style="font-weight: 700; font-size: 1.1rem; margin-bottom: 10px; color: #ffffff;">Q{i+1}: {q_item.get('q', 'Question Item Schema')}</p>
                </div>
                """, unsafe_allow_html=True)
                
                options = q_item.get("options", [])
                if not isinstance(options, list): options = []
                while len(options) < 4: options.append(f"Option {len(options)+1}")

                option_map = {"A": options[0], "B": options[1], "C": options[2], "D": options[3]}
                user_sel = st.radio(f"Select Answer for Q{i+1}:", ["A", "B", "C", "D"], format_func=lambda x: f"{x}. {option_map[x]}", key=f"dynamic_quiz_rad_{i}")
                selections.append(user_sel)
                st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
            
            if st.button("Audit Evaluation Matrix Scores", key="audit_btn"):
                correct_answers = [q.get("ans", "A").upper().strip() for q in questions_list]
                score_metrics = sum(1 for u, c in zip(selections, correct_answers) if u == c)
                st.session_state.quiz_scores[data['topic']] = score_metrics
                if score_metrics >= len(questions_list)/2:
                    st.success(f"🏆 Review Passed: Achieved {score_metrics}/{len(questions_list)} correct answers!")
                else:
                    st.error(f"📉 Optimization Suggested: Score {score_metrics}/{len(questions_list)}. Re-evaluate structural facts.")
        else:
            st.info("No active quiz diagnostic dataset found for this topic.")

    with tab3:
        st.markdown("### ⚡ Rapid Retrieval Flashcards")
        flashcards_text = data.get("flashcards", "")
        
        questions_found = re.findall(r"Q:\s*(.*?)(?=A:|\n\n|Q:|$)", flashcards_text, re.DOTALL)
        answers_found = re.findall(r"A:\s*(.*?)(?=Q:|\n\n|A:|$)", flashcards_text, re.DOTALL)
        
        card_counter = 1
        if questions_found and answers_found:
            for q_part, a_part in zip(questions_found, answers_found):
                q_clean = q_part.strip()
                a_clean = a_part.strip()
                if q_clean and a_clean:
                    st.markdown(f"""
                    <div class="glowing-flashcard" style="padding:24px;">
                        <h5 style="color: #818cf8; margin-top: 0; font-weight: 700;">⚡ Flashcard {card_counter}</h5>
                        <p style="margin-bottom: 12px; font-size: 1.1rem; color: #ffffff;"><b style="color: #38bdf8;">Q:</b> {q_clean}</p>
                        <p style="margin-top: 4px; font-size: 1rem; color: #cbd5e1;"><b style="color: #34d399;">A:</b> {a_clean}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    card_counter += 1
        else:
            st.info("No structured flashcards found.")
            
    with tab4:
        st.markdown("### 📊 Learning Diagnostics & Engagement Metrics")
        if data['topic'] in st.session_state.quiz_scores:
            latest_score = st.session_state.quiz_scores[data['topic']]
            st.metric(label="Latest Diagnostic Quiz Performance", value=f"{latest_score} / 8 Correct")
            st.progress(latest_score / 8)
        else:
            st.info("Pass the diagnostic test inside Tab 2 to view performance analytics metrics.")


st.markdown("""
<div style="
margin-top:60px;
padding:25px;
text-align:center;
border-top:1px solid rgba(255,255,255,0.08);
background:rgba(15,23,42,.25);
backdrop-filter:blur(10px);
border-radius:15px;
">

<h4 style="
margin-bottom:8px;
font-weight:800;
font-size:24px;
">
🧠
<span style="
background:linear-gradient(90deg,#60a5fa,#818cf8,#22d3ee);
-webkit-background-clip:text;
-webkit-text-fill-color:transparent;
">
Nexus Cognitive Engine
</span>
</h4>

<p style="color:#cbd5e1;font-size:15px;margin-bottom:8px;">
Designed & Developed by <b>Shirsam Bhattacharjee</b>
</p>

<p style="color:#94a3b8;font-size:13px;margin-bottom:8px;">
AI-Powered Learning & Research Platform
</p>

<p style="color:#64748b;font-size:12px;">
© 2026 Shirsam Bhattacharjee. All Rights Reserved.
</p>

</div>
""", unsafe_allow_html=True)
