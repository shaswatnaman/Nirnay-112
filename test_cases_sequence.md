# Test Case Sequence to Fill All Incident Fields

Say these 10 statements **in order** during a call session to fill all fields:

## Sequence:

1. **"मेरा नाम राहुल शर्मा है"** (My name is Rahul Sharma)
   - **Fills**: Caller Name → "Rahul Sharma"

2. **"मुझे दिल्ली में एक दुर्घटना हुई है"** (I had an accident in Delhi)
   - **Fills**: Location → "Delhi"
   - **Fills**: Incident Type → "road_accident" (from "दुर्घटना")

3. **"गाड़ी से टक्कर हो गई"** (Car collision happened)
   - **Confirms**: Incident Type → "road_accident" (strengthens confidence)

4. **"दो लोगों को चोट लगी है"** (Two people are injured)
   - **Fills**: People Affected → 2

5. **"जल्दी भेजो, बहुत खून बह रहा है"** (Send quickly, a lot of blood is flowing)
   - **Triggers**: Escalation Status (high urgency from "जल्दी", "खून बह रहा")

6. **"मेरा नाम अमित कुमार है"** (My name is Amit Kumar)
   - **Updates**: Caller Name → "Amit Kumar" (if confidence higher)

7. **"मुंबई के नेरुल स्टेशन के पास"** (Near Nerul station in Mumbai)
   - **Updates**: Location → "Nerul station, Mumbai" (more specific)

8. **"तीन लोग घायल हैं"** (Three people are injured)
   - **Updates**: People Affected → 3 (if confidence higher)

9. **"बहुत जरूरी है, तुरंत आओ"** (Very urgent, come immediately)
   - **Maintains**: Escalation Status (high urgency maintained)

10. **"एक व्यक्ति बेहोश हो गया है"** (One person has become unconscious)
    - **Updates**: People Affected → 1 (if mentioned separately)
    - **Maintains**: Incident Type → "road_accident" or may shift to "medical_emergency"

---

## Alternative Sequences (if first doesn't work):

### Medical Emergency Sequence:
1. "मेरा नाम प्रिया है" (My name is Priya)
2. "बैंगलोर में मेरे पिता को हार्ट अटैक आया है" (My father had a heart attack in Bangalore)
3. "बहुत जरूरी है, जल्दी भेजो" (Very urgent, send quickly)
4. "एक व्यक्ति प्रभावित है" (One person affected)

### Fire Emergency Sequence:
1. "मेरा नाम विवेक है" (My name is Vivek)
2. "चेन्नई में मेरे घर में आग लग गई है" (Fire broke out in my house in Chennai)
3. "पांच लोग फंसे हुए हैं" (Five people are trapped)
4. "तुरंत भेजो, धुआं बहुत है" (Send immediately, there's a lot of smoke)

### Crime Sequence:
1. "मेरा नाम सीमा है" (My name is Seema)
2. "कोलकाता में चोरी हो गई है" (Theft happened in Kolkata)
3. "दो लोग शामिल हैं" (Two people are involved)

---

## Key Phrases to Remember:

**For Name:**
- "मेरा नाम [NAME] है"
- "I am [NAME]"
- "My name is [NAME]"

**For Location:**
- "[PLACE] में" (in [PLACE])
- "near [PLACE]"
- "[PLACE] के पास" (near [PLACE])
- City names: दिल्ली, मुंबई, बैंगलोर, चेन्नई, कोलकाता

**For Incident Type:**
- Medical: "चोट", "injury", "heart attack", "bleeding", "unconscious"
- Fire: "आग", "fire", "aag lag gayi", "smoke"
- Crime: "चोरी", "theft", "robbery", "loot"
- Accident: "दुर्घटना", "accident", "टक्कर"
- Natural Disaster: "flood", "भूकंप", "earthquake"

**For People Affected:**
- "दो लोग" (two people)
- "तीन लोग" (three people)
- "कितने लोग" (how many people)
- "एक व्यक्ति" (one person)

**For Escalation (High Urgency):**
- "जल्दी", "तुरंत", "बहुत जरूरी" (quickly, immediately, very urgent)
- "खून बह रहा", "bleeding", "unconscious"
- "फंसे हुए", "trapped", "danger"

