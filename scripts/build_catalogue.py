"""Build the shared catalogue. Hindi/Marathi drafts require native review."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# en | hi | mr. Stable generated UI keys preserve the English source phrase.
ROWS = '''
Daily|दैनिक|दैनिक
Messages|संदेश|संदेश
Insights|विश्लेषण|विश्लेषण
Setup|व्यवस्था|व्यवस्था
Admin|व्यवस्थापक|प्रशासक
Principal|प्रधानाचार्य|मुख्याध्यापक
Teacher|शिक्षक|शिक्षक
Staff|कर्मचारी|कर्मचारी
Parent|अभिभावक|पालक
Kid|बच्चे|मुले
Publish the plan|योजना प्रकाशित करें|योजना प्रकाशित करा
My class|मेरी कक्षा|माझा वर्ग
Duty and gate|ड्यूटी और गेट|ड्युटी आणि गेट
Today for my child|मेरे बच्चे का आज|माझ्या मुलाचा आजचा दिवस
Air Explorer|हवा के खोजी|हवेचा शोधक
Current school planning priority|स्कूल की मौजूदा योजना की प्राथमिकता|शाळेच्या सध्याच्या योजनेचे प्राधान्य
Move PE and assembly indoors|खेल और सभा को अंदर रखें|खेळ आणि सभा वर्गात घ्या
Rotate outdoor duties and take indoor breaks|बाहरी ड्यूटी बदलें और अंदर विश्राम करें|मैदानी ड्युटी बदला आणि आत विश्रांती घ्या
Review shorter, gentler outdoor activities|छोटी और हल्की बाहरी गतिविधियाँ चुनें|लहान आणि हलके मैदानी उपक्रम निवडा
Review the usual school timetable|स्कूल की सामान्य समय-सारणी देखें|शाळेचे नेहमीचे वेळापत्रक तपासा
Reduce waiting at the school gate|स्कूल गेट पर इंतज़ार कम करें|शाळेच्या गेटवरील थांबा कमी करा
Verify current air conditions|हवा की मौजूदा स्थिति जाँचें|हवेची सध्याची स्थिती तपासा
Suggested change. Check room conditions before confirming.|सुझाया गया बदलाव। पुष्टि से पहले कमरे की स्थिति जाँचें।|सुचवलेला बदल. पुष्टी करण्यापूर्वी खोलीची स्थिती तपासा.
School planning suggestion. Follow the published school instruction.|स्कूल योजना का सुझाव। प्रकाशित स्कूल निर्देश मानें।|शाळेच्या योजनेचा सल्ला. प्रकाशित शाळेची सूचना पाळा.
Fresh air data is needed. Publication is paused.|हवा की नई जानकारी चाहिए। प्रकाशन रुका हुआ है।|हवेची ताजी माहिती हवी. प्रकाशन थांबवले आहे.
Planning bands, not official AQI|योजना के स्तर, आधिकारिक AQI नहीं|योजनेचे स्तर, अधिकृत AQI नाही
Plan reviews|योजना की समीक्षाएँ|योजनेचे आढावे
Reviews {0} of {1}|समीक्षाएँ {0} / {1}|आढावे {0} / {1}
Waiting|प्रतीक्षा|प्रतीक्षेत
Reviewed|समीक्षित|आढावा घेतला
Published|प्रकाशित|प्रकाशित
Draft|मसौदा|मसुदा
Not yet shared|अभी साझा नहीं किया|अजून सामायिक नाही
School administrator|स्कूल व्यवस्थापक|शाळा प्रशासक
Parent / guardian|अभिभावक|पालक
School duty team|स्कूल ड्यूटी दल|शाळेचे ड्युटी पथक
Records review, not health outcomes.|यह समीक्षा की नोंद है, स्वास्थ्य परिणाम नहीं।|ही आढाव्याची नोंद आहे, आरोग्य परिणाम नाहीत.
This draft has no confirmations. Publish it before requesting reviews.|इस मसौदे की पुष्टि नहीं हुई। समीक्षा माँगने से पहले प्रकाशित करें।|या मसुद्याची पुष्टी नाही. आढावा मागण्यापूर्वी प्रकाशित करा.
Publish plan|योजना प्रकाशित करें|योजना प्रकाशित करा
Draft a revision|नया मसौदा बनाएँ|नवा मसुदा तयार करा
Edit wording|शब्द बदलें|मजकूर बदला
What changes · outdoor minutes at orange/red|बदलाव · नारंगी/लाल स्तर पर बाहरी मिनट|बदल · नारंगी/लाल स्तरातील मैदानी मिनिटे
Planning estimate if the suggested changes are reviewed and followed.|सुझावों की समीक्षा करके अपनाने पर योजना का अनुमान।|सूचनांचा आढावा घेऊन पालन केल्यास योजनेचा अंदाज.
Published school plan|प्रकाशित स्कूल योजना|प्रकाशित शाळेची योजना
Draft school plan|स्कूल योजना का मसौदा|शाळेच्या योजनेचा मसुदा
The school instruction is published.|स्कूल का निर्देश प्रकाशित है।|शाळेची सूचना प्रकाशित आहे.
Review the new draft before sharing.|साझा करने से पहले नए मसौदे की समीक्षा करें।|सामायिक करण्यापूर्वी नव्या मसुद्याचा आढावा घ्या.
Read school plan|स्कूल योजना पढ़ें|शाळेची योजना वाचा
Review draft|मसौदा देखें|मसुदा तपासा
Morning brief|सुबह की जानकारी|सकाळची माहिती
Tomorrow’s forecast|कल का पूर्वानुमान|उद्याचा अंदाज
Move PE and assembly indoors?|क्या खेल और सभा अंदर रखें?|खेळ आणि सभा वर्गात घ्यायची का?
Yes — review indoor alternatives.|हाँ — अंदर के विकल्प देखें।|हो — आतील पर्याय तपासा.
No — review the usual timetable.|नहीं — सामान्य समय-सारणी देखें।|नाही — नेहमीचे वेळापत्रक तपासा.
Unknown — forecast unavailable; verify with staff.|अज्ञात — पूर्वानुमान उपलब्ध नहीं; कर्मचारियों से जाँचें।|अज्ञात — अंदाज उपलब्ध नाही; कर्मचाऱ्यांना विचारा.
Demo forecast|नमूना पूर्वानुमान|नमुना अंदाज
Draft the morning message|सुबह का संदेश बनाएँ|सकाळचा संदेश तयार करा
What changes in the school day|स्कूल के दिन में बदलाव|शाळेच्या दिवसातील बदल
Planned outdoors at orange or red|नारंगी या लाल स्तर पर बाहरी योजना|नारंगी किंवा लाल स्तरावर मैदानी योजना
Data health|डेटा की स्थिति|माहितीची स्थिती
Fresh|ताज़ा|ताजी
Getting old|पुरानी हो रही है|जुनी होत आहे
Stale|पुराना|जुनी
Unavailable|उपलब्ध नहीं|उपलब्ध नाही
Your school day|आपका स्कूल दिवस|तुमचा शाळेचा दिवस
School-day blocks for your class|आपकी कक्षा के दैनिक हिस्से|तुमच्या वर्गाचे दिवसभरातील भाग
Suggestions to review with a school adult.|स्कूल के जिम्मेदार वयस्क के साथ सुझाव देखें।|शाळेतील जबाबदार प्रौढासोबत सूचना तपासा.
Assembly|सभा|प्रार्थना सभा
PE|खेल|खेळ
Break|विराम|सुट्टी
Pickup|बच्चे को लेने का समय|मुलाला घेण्याची वेळ
No change|कोई बदलाव नहीं|बदल नाही
Why this matters|यह क्यों ज़रूरी है|हे महत्त्वाचे का आहे
Your next steps|आपके अगले कदम|तुमची पुढची पावले
Sources|स्रोत|स्रोत
Data sources|डेटा स्रोत|माहितीचे स्रोत
Public-source registry|सार्वजनिक स्रोत सूची|सार्वजनिक स्रोत यादी
Where this reading came from|यह जानकारी कहाँ से आई|ही माहिती कुठून आली
Source details & explanation|स्रोत का विवरण और कारण|स्रोताचा तपशील आणि स्पष्टीकरण
Plan an outdoor activity|बाहरी गतिविधि की योजना|मैदानी उपक्रमाची योजना
Look ahead|आगे की योजना|पुढची योजना
Valid time|लागू समय|लागू वेळ
Source|स्रोत|स्रोत
Retrieved|प्राप्त|मिळवले
Activity start (local time)|गतिविधि शुरू (स्थानीय समय)|उपक्रम सुरू (स्थानिक वेळ)
Activity duration in minutes|गतिविधि की अवधि (मिनट)|उपक्रमाचा कालावधी (मिनिटे)
Review activity window|गतिविधि का समय जाँचें|उपक्रमाची वेळ तपासा
Weather context|मौसम की जानकारी|हवामानाची माहिती
Your class|आपकी कक्षा|तुमचा वर्ग
Class timetable|कक्षा की समय-सारणी|वर्गाचे वेळापत्रक
Class checklist|कक्षा की कार्यसूची|वर्गाची कृती यादी
Duty checklist|ड्यूटी कार्यसूची|ड्युटी कृती यादी
Your duty briefing|आपकी ड्यूटी की जानकारी|तुमच्या ड्युटीची माहिती
A message from your school|आपके स्कूल का संदेश|तुमच्या शाळेचा संदेश
School-linked class|स्कूल से जुड़ी कक्षा|शाळेशी जोडलेला वर्ग
Class not linked|कक्षा जुड़ी नहीं है|वर्ग जोडलेला नाही
Mark as read|पढ़ लिया है|वाचले म्हणून नोंदवा
Review recorded|समीक्षा दर्ज है|आढावा नोंदवला
Read the full school plan|पूरी स्कूल योजना पढ़ें|शाळेची संपूर्ण योजना वाचा
Read the full duty plan|पूरी ड्यूटी योजना पढ़ें|संपूर्ण ड्युटी योजना वाचा
Review & acknowledge class plan|कक्षा की योजना देखें और पुष्टि करें|वर्गाची योजना तपासा आणि मान्य करा
Open my class details|मेरी कक्षा का विवरण|माझ्या वर्गाचा तपशील
Confirm completed|पूरा होने की पुष्टि करें|पूर्ण झाल्याची पुष्टी करा
Completion recorded|पूर्णता दर्ज है|पूर्णता नोंदवली
Air evidence & planning tools|हवा का डेटा और योजना के साधन|हवेची माहिती आणि नियोजन साधने
School instruction · original wording|स्कूल निर्देश · मूल शब्द|शाळेची सूचना · मूळ मजकूर
School wording is not automatically translated.|स्कूल के अपने शब्द अपने आप अनुवादित नहीं होते।|शाळेचा मूळ मजकूर आपोआप अनुवादित केला जात नाही.
The shared school plan|साझा स्कूल योजना|सामायिक शाळेची योजना
School instruction|स्कूल निर्देश|शाळेची सूचना
I read the latest notice|मैंने नई सूचना पढ़ी है|मी नवीन सूचना वाचली
I confirmed the room and supervision|मैंने कमरे और निगरानी की पुष्टि की है|मी खोली आणि देखरेखीची खात्री केली
I told the class what changes|मैंने कक्षा को बदलाव बताए हैं|मी वर्गाला बदल सांगितले
Reset to suggestion|सुझाव पर वापस जाएँ|सूचनेकडे परत जा
Preview language|नमूने की भाषा|नमुन्याची भाषा
Print notice|सूचना प्रिंट करें|सूचना छापा
Explicit completion receipts|पूरा होने की स्पष्ट पुष्टि|पूर्णतेच्या स्पष्ट नोंदी
Your plan checklist|आपकी योजना कार्यसूची|तुमच्या योजनेची कृती यादी
Confirm reviewed and completed|समीक्षा और पूर्णता की पुष्टि करें|आढावा आणि पूर्णतेची पुष्टी करा
No school notice has been published.|स्कूल की सूचना अभी प्रकाशित नहीं है।|शाळेची सूचना अद्याप प्रकाशित नाही.
Earlier published instruction|पहले का प्रकाशित निर्देश|आधीची प्रकाशित सूचना
No children linked to this class.|इस कक्षा से बच्चे जुड़े नहीं हैं।|या वर्गाशी मुले जोडलेली नाहीत.
Your notifications|आपकी सूचनाएँ|तुमच्या सूचना
Message language|संदेश की भाषा|संदेशाची भाषा
Quiet hours start|शांत समय शुरू|शांत वेळ सुरू
Quiet hours end|शांत समय समाप्त|शांत वेळ समाप्त
Daily cap per channel|हर माध्यम की दैनिक सीमा|प्रत्येक माध्यमाची दैनिक मर्यादा
Channels you consent to receive|आपकी अनुमति वाले माध्यम|तुम्ही परवानगी दिलेली माध्यमे
Morning school-plan update|सुबह की स्कूल योजना सूचना|सकाळची शाळेची योजना सूचना
Save preferences|विकल्प सहेजें|प्राधान्ये जतन करा
Delivery history|भेजने का इतिहास|वितरण इतिहास
No delivery attempts recorded.|भेजने का प्रयास दर्ज नहीं है।|वितरणाचा प्रयत्न नोंदवलेला नाही.
Today’s channel limits|आज की माध्यम सीमाएँ|आजच्या माध्यमांच्या मर्यादा
Send a test to me|मुझे परीक्षण संदेश भेजें|मला चाचणी संदेश पाठवा
Remind unread adults|जिन्होंने नहीं पढ़ा उन्हें याद दिलाएँ|न वाचलेल्या प्रौढांना आठवण करा
Remind|याद दिलाएँ|आठवण करा
School send log|स्कूल संदेश इतिहास|शाळेचा संदेश इतिहास
Time|समय|वेळ
Audience|प्राप्तकर्ता|प्राप्तकर्ते
Channel|माध्यम|माध्यम
Language|भाषा|भाषा
Status|स्थिति|स्थिती
in-app|ऐप में|ॲपमध्ये
push|पुश सूचना|पुश सूचना
email|ईमेल|ईमेल
sms|SMS|SMS
whatsapp|WhatsApp|WhatsApp
Classes|कक्षाएँ|वर्ग
Your class plan|आपकी कक्षा की योजना|तुमच्या वर्गाची योजना
Class plans|कक्षाओं की योजनाएँ|वर्गांच्या योजना
Class|कक्षा|वर्ग
Acknowledged|पुष्टि हुई|मान्य केले
Not acknowledged|पुष्टि नहीं हुई|मान्य केले नाही
Plan awaiting publication|योजना प्रकाशन की प्रतीक्षा में|योजना प्रकाशनाच्या प्रतीक्षेत
View school plan|स्कूल योजना देखें|शाळेची योजना पाहा
School-day planning estimate|स्कूल दिवस की योजना का अनुमान|शाळेच्या दिवसाच्या योजनेचा अंदाज
Refresh|फिर जाँचें|पुन्हा तपासा
Refresh demo fixtures|नमूना डेटा फिर लाएँ|नमुना माहिती पुन्हा आणा
Demo tools…|नमूना साधन…|नमुना साधने…
Demo tools|नमूना साधन|नमुना साधने
Close|बंद करें|बंद करा
Choose scenario|परिस्थिति चुनें|परिस्थिती निवडा
Green|हरा|हिरवा
Yellow|पीला|पिवळा
Orange|नारंगी|नारंगी
Red|लाल|लाल
Unknown|अज्ञात|अज्ञात
green|हरा|हिरवा
yellow|पीला|पिवळा
orange|नारंगी|नारंगी
red|लाल|लाल
unknown|अज्ञात|अज्ञात
Demo data|नमूना डेटा|नमुना माहिती
Demo data · synthetic station fixtures|नमूना डेटा · कृत्रिम स्टेशन रीडिंग|नमुना माहिती · कृत्रिम केंद्र रीडिंग
Synthetic preview fixtures|कृत्रिम नमूना डेटा|कृत्रिम नमुना माहिती
Demo fixtures|नमूना डेटा|नमुना माहिती
Not live measurements|वास्तविक माप नहीं|प्रत्यक्ष मोजमाप नाही
Synthetic forecast fixture|कृत्रिम पूर्वानुमान नमूना|कृत्रिम अंदाज नमुना
Demo workspace. Sample data. No messages are sent.|नमूना कार्यस्थल। उदाहरण डेटा। संदेश नहीं भेजे जाते।|नमुना कार्यस्थान. उदाहरण माहिती. संदेश पाठवले जात नाहीत.
School air quality & action platform|स्कूल की हवा और कार्य योजना का मंच|शाळेच्या हवेची गुणवत्ता आणि कृती मंच
Skip to school workspace|स्कूल कार्यस्थल पर जाएँ|शाळेच्या कार्यस्थानाकडे जा
Skip to content|मुख्य सामग्री पर जाएँ|मुख्य मजकुराकडे जा
Back to home|मुखपृष्ठ पर जाएँ|मुखपृष्ठावर जा
Keep your school day coordinated.|स्कूल के दिन की योजना साथ रखें।|शाळेच्या दिवसाची योजना एकत्र ठेवा.
Check the air. Review the school plan.|हवा जाँचें। स्कूल योजना देखें।|हवा तपासा. शाळेच्या योजनेचा आढावा घ्या.
School workspace updated.|स्कूल की जानकारी फिर जाँची गई।|शाळेची माहिती पुन्हा तपासली.
Review saved.|समीक्षा सहेजी गई।|आढावा जतन केला.
Published.|प्रकाशित हुआ।|प्रकाशित केले.
Preferences saved.|विकल्प सहेजे गए।|प्राधान्ये जतन केली.
Completion recorded.|पूर्णता दर्ज हुई।|पूर्णता नोंदवली.
Haze is illustrative|धुंध केवल चित्रण है|धुके केवळ चित्रण आहे
Reduce effects|दृश्य प्रभाव कम करें|दृश्य परिणाम कमी करा
Larger text|बड़ा पाठ|मोठा मजकूर
Update available|अपडेट उपलब्ध है|अद्यतन उपलब्ध आहे
Reload to update|अपडेट के लिए फिर खोलें|अद्यतनासाठी पुन्हा उघडा
Offline · last known plan; writes are paused.|ऑफ़लाइन · पिछली योजना; बदलाव रुके हैं।|ऑफलाइन · मागील योजना; बदल थांबवले आहेत.
System status|सिस्टम की स्थिति|यंत्रणेची स्थिती
Cleaner activity windows|गतिविधि के लिए साफ़ हवा का समय|उपक्रमांसाठी स्वच्छ हवेची वेळ
Planning estimate|योजना का अनुमान|योजनेचा अंदाज
No complete forecast window is available.|पूरा पूर्वानुमान उपलब्ध नहीं है।|संपूर्ण अंदाज उपलब्ध नाही.
No safer time or activity clearance is implied.|सुरक्षित समय या गतिविधि की अनुमति का दावा नहीं है।|सुरक्षित वेळ किंवा उपक्रमाची परवानगी सूचित होत नाही.
School adult override|स्कूल वयस्क का बदलाव|शाळेतील प्रौढाचा बदल
Keep outdoors|गतिविधि बाहर रखें|उपक्रम मैदानात ठेवा
Required reason|कारण ज़रूरी है|कारण आवश्यक आहे
Record decision|निर्णय दर्ज करें|निर्णय नोंदवा
Recorded decision does not establish safe air.|निर्णय की नोंद हवा की सुरक्षा साबित नहीं करती।|नोंदवलेला निर्णय हवा सुरक्षित असल्याचे सिद्ध करत नाही.
Waiting since {0}|{0} से प्रतीक्षा|{0} पासून प्रतीक्षा
Observation: {0}|अवलोकन: {0}|निरीक्षण: {0}
Successful retrieval: {0}|सफल प्राप्ति: {0}|यशस्वी प्राप्ती: {0}
Published · {0}|प्रकाशित · {0}|प्रकाशित · {0}
Published {0}|प्रकाशित {0}|प्रकाशित {0}
Valid {0}|लागू {0}|लागू {0}
Retrieved {0}|प्राप्त {0}|मिळवले {0}
Planned outdoors · {0} min|बाहर नियोजित · {0} मिनट|मैदानात नियोजित · {0} मिनिटे
{0} → {1} min|{0} → {1} मिनट|{0} → {1} मिनिटे
{0} teacher|{0} शिक्षक|{0} शिक्षक
Viewing as: {0}|भूमिका: {0}|भूमिका: {0}
{0} workspace|{0} कार्यस्थल|{0} कार्यस्थान
Demo clock {0} IST|नमूना घड़ी {0} IST|नमुना घड्याळ {0} IST
{0} minutes since observation|अवलोकन के बाद {0} मिनट|निरीक्षणानंतर {0} मिनिटे
{0} linked students · {1} need extra caution|{0} जुड़े विद्यार्थी · {1} को अतिरिक्त सावधानी|{0} जोडलेले विद्यार्थी · {1} साठी अधिक काळजी
needs native review|मातृभाषी समीक्षा आवश्यक|मातृभाषिकाचा आढावा आवश्यक
Read the plan with a grown-up.|किसी बड़े के साथ योजना पढ़ें।|मोठ्यांसोबत योजना वाचा.
Ask your teacher where your class will play.|आपकी कक्षा कहाँ खेलेगी, शिक्षक से पूछें।|तुमचा वर्ग कुठे खेळेल, शिक्षकांना विचारा.
Tell an adult if you feel unwell.|तबीयत ठीक न लगे तो बड़े को बताएँ।|बरे वाटत नसेल तर मोठ्यांना सांगा.
Your school says indoor play today. What would you do?|स्कूल ने आज अंदर खेलने को कहा है। आप क्या करेंगे?|शाळेने आज आत खेळायला सांगितले आहे. तुम्ही काय कराल?
Ask my teacher what’s planned|शिक्षक से योजना पूछूँगा|शिक्षकांना योजना विचारेन
Choose outdoor play on my own|अपने आप बाहर खेलूँगा|स्वतः मैदानात खेळेन
You earned an Air Explorer sticker!|आपको हवा के खोजी का स्टिकर मिला!|तुला हवेच्या शोधकाचे स्टिकर मिळाले!
Ask your teacher first. They know the school plan.|पहले शिक्षक से पूछें। उन्हें स्कूल योजना पता है।|आधी शिक्षकांना विचारा. त्यांना शाळेची योजना माहीत आहे.
Next question|अगला प्रश्न|पुढचा प्रश्न
Try again|फिर कोशिश करें|पुन्हा प्रयत्न करा
Back to question|प्रश्न पर वापस|प्रश्नाकडे परत
Reset demo|नमूना रीसेट करें|नमुना पुन्हा सुरू करा
Story mode|प्रस्तुति के चरण|प्रात्यक्षिकाचे टप्पे
Next step|अगला कदम|पुढची पायरी
Story: {0} of {1}|प्रस्तुति: {0} / {1}|प्रात्यक्षिक: {0} / {1}
Home|मुखपृष्ठ|मुखपृष्ठ
Receipts|पुष्टि की नोंद|पुष्टी नोंदी
'''


def build():
    legacy = json.loads((ROOT / 'assets' / 'legacy-phrases.json').read_text(encoding='utf-8'))
    entries = {}
    for en, hi in legacy['hi'].items():
        if en in legacy['mr']:
            key = 'ui.' + hashlib.sha256(en.encode()).hexdigest()[:12]
            entries[key] = {'en': en, 'hi': hi, 'mr': legacy['mr'][en]}
    for row in (ROWS.strip()+'\n'+(ROOT/'scripts'/'catalogue_extra.txt').read_text(encoding='utf-8').strip()).splitlines():
        en, hi, mr = row.split('|')
        key = 'ui.' + hashlib.sha256(en.encode()).hexdigest()[:12]
        entries[key] = {'en': en, 'hi': hi, 'mr': mr}
    from backend.functions.guardian_rules import recommendations
    from cloud.messages import role_message
    # Engine action codes are the canonical semantic keys used on the server too.
    action_rows = {
        'verify': ('Ask school staff to verify conditions before making an activity decision.', 'गतिविधि की योजना से पहले स्कूल कर्मचारियों से स्थिति की पुष्टि कराएँ।', 'उपक्रम ठरवण्यापूर्वी शाळेच्या कर्मचाऱ्यांकडून स्थितीची खात्री करा.'),
        'indoor-pe': ('Review moving vigorous PE and assembly indoors; check room conditions before confirming.', 'तेज़ खेल और सभा अंदर करने की योजना देखें; पुष्टि से पहले कमरे की स्थिति जाँचें।', 'जोराचे खेळ आणि सभा आत घेण्याचा विचार करा; पुष्टीपूर्वी खोलीची स्थिती तपासा.'),
        'gentle': ('Review shorter, gentler outdoor activities and recheck conditions before starting.', 'छोटी, हल्की बाहरी गतिविधियाँ चुनें और शुरू करने से पहले स्थिति फिर जाँचें।', 'लहान, हलके मैदानी उपक्रम निवडा आणि सुरू करण्यापूर्वी स्थिती पुन्हा तपासा.'),
        'usual': ('Review the usual timetable and recheck the air before long outdoor sessions.', 'सामान्य समय-सारणी देखें और लंबे बाहरी सत्र से पहले हवा फिर जाँचें।', 'नेहमीचे वेळापत्रक तपासा आणि दीर्घ मैदानी उपक्रमापूर्वी हवा पुन्हा तपासा.'),
        'pickup': ('Stagger pickup/drop-off and reduce waiting at the gate; ask drivers to avoid unnecessary idling.', 'आने-जाने का समय अलग रखें और गेट पर इंतज़ार कम करें; चालकों से बेकार इंजन चालू न रखने को कहें।', 'येण्या-जाण्याच्या वेळा वेगळ्या ठेवा आणि गेटवरील थांबा कमी करा; चालकांना विनाकारण इंजिन सुरू ठेवू नका असे सांगा.'),
        'rotate': ('Ask the supervisor to rotate outdoor gate and ground duties and provide indoor breaks.', 'पर्यवेक्षक से गेट और मैदान की बाहरी ड्यूटी बदलने और अंदर विश्राम देने को कहें।', 'पर्यवेक्षकांना मैदानी ड्युटी बदलायला आणि आत विश्रांती द्यायला सांगा.'),
        'mask': ('Ask a responsible adult or supervisor about a well-fitting N95/KN95 reminder where school guidance and an existing care plan call for one. Adult respirator fit is not assumed for children.', 'स्कूल निर्देश और देखभाल योजना के अनुसार उपयुक्त N95/KN95 के बारे में जिम्मेदार बड़े से पूछें। वयस्क मास्क का फिट बच्चों के लिए नहीं माना जाता।', 'शाळेच्या सूचना आणि काळजी योजनेनुसार योग्य N95/KN95 बाबत जबाबदार प्रौढाला विचारा. प्रौढांचा मास्क मुलांना योग्य बसेल असे गृहीत नाही.'),
        'route': ('Discuss avoiding high-traffic roads and unnecessary outdoor stops with an adult. Use route estimates as planning comparisons, not proof that a road is clean.', 'व्यस्त सड़कें और बेकार बाहरी ठहराव टालने के लिए बड़े से बात करें। मार्ग के अनुमान तुलना हैं, साफ़ हवा का प्रमाण नहीं।', 'वर्दळीचे रस्ते आणि विनाकारण मैदानी थांबे टाळण्याबाबत मोठ्यांशी बोला. मार्गांचे अंदाज तुलना आहेत, स्वच्छ हवेचा पुरावा नाही.'),
        'care-plan': ('Keep following existing school instructions and care plans; tell a trusted adult if you feel unwell.', 'स्कूल निर्देश और देखभाल योजना मानते रहें; तबीयत ठीक न हो तो भरोसेमंद बड़े को बताएँ।', 'शाळेच्या सूचना आणि काळजी योजना पाळा; बरे वाटत नसल्यास विश्वासू प्रौढाला सांगा.'),
        'peak': ('At the predicted pollution peak, staff should review keeping windows closed if indoor air and ventilation/heat conditions support it; follow the building plan.', 'प्रदूषण के अनुमानित चरम पर, अंदर की हवा और गर्मी/वेंटिलेशन ठीक होने पर कर्मचारी खिड़कियाँ बंद रखने पर विचार करें; भवन योजना मानें।', 'प्रदूषणाच्या अंदाजित उच्च काळात, आतील हवा आणि उष्णता/वायुवीजन योग्य असल्यास खिडक्या बंद ठेवण्याचा विचार करा; इमारतीची योजना पाळा.'),
        'indoor-check': ('Review the room air before relying on an indoor alternative.', 'अंदर के विकल्प पर भरोसा करने से पहले कमरे की हवा जाँचें।', 'आतील पर्यायावर अवलंबून राहण्यापूर्वी खोलीची हवा तपासा.')}
    for key, row in action_rows.items():
        entries['action.' + key] = dict(zip(['en', 'hi', 'mr'], row))
    entries['notification.prefix']={'en':'School flag','hi':'स्कूल संकेत','mr':'शाळेचा इशारा'}
    entries['notification.title']={'en':'Air Guardian school update','hi':'Air Guardian स्कूल सूचना','mr':'Air Guardian शाळेची सूचना'}
    entries['ui.native-review']={'en':'Translation draft · needs native review','hi':'अनुवाद का मसौदा · मातृभाषी समीक्षा आवश्यक','mr':'अनुवादाचा मसुदा · मातृभाषिक पुनरावलोकन आवश्यक'}
    entries['kid.question']={'en':'Your school says indoor play today. What would you do?','hi':'स्कूल कहता है आज अंदर खेलें। आप क्या करेंगे?','mr':'शाळा सांगते आज आत खेळा. तुम्ही काय कराल?'}
    for code, en, hi, mr in [
        ('verify', 'Ask a grown-up for today’s school plan.', 'बड़े से आज की स्कूल योजना पूछें।', 'मोठ्यांना आजची शाळेची योजना विचारा.'),
        ('indoor-pe', 'Ask your teacher about playing indoors today.', 'शिक्षक से आज अंदर खेलने के बारे में पूछें।', 'आज आत खेळण्याबद्दल शिक्षकांना विचारा.'),
        ('gentle', 'Ask your teacher about shorter outdoor play.', 'शिक्षक से थोड़ी देर बाहर खेलने के बारे में पूछें।', 'थोडा वेळ बाहेर खेळण्याबद्दल शिक्षकांना विचारा.'),
        ('usual', 'Ask your teacher what your class has planned today.', 'शिक्षक से पूछें आज कक्षा की क्या योजना है।', 'आज वर्गाची काय योजना आहे ते शिक्षकांना विचारा.')]:
        entries['kid.action.'+code]={'en':en,'hi':hi,'mr':mr}
    for en,hi,mr in [('green','हरा','हिरवा'),('yellow','पीला','पिवळा'),('orange','नारंगी','नारंगी'),('red','लाल','लाल'),('unknown','अज्ञात','अज्ञात')]:
        entries['flag.'+en]={'en':en,'hi':hi,'mr':mr}
    for code,en,hi,mr in [
        ('usual','Keep the usual school timetable','स्कूल की सामान्य समय-सारणी रखें','शाळेचे नेहमीचे वेळापत्रक ठेवा'),
        ('gentle','Shorter, gentler outdoor activities','बाहर छोटी और हल्की गतिविधियाँ करें','मैदानी उपक्रम लहान आणि हलके ठेवा'),
        ('indoor-pe','Move PE and assembly indoors','खेल और सभा को अंदर रखें','खेळ आणि सभा वर्गात घ्या'),
        ('verify','Verify conditions before outdoor activities','बाहरी गतिविधियों से पहले स्थिति जाँचें','मैदानी उपक्रमांपूर्वी परिस्थिती तपासा'),
        ('rotate','Rotate outdoor duties and take indoor breaks','बाहरी ड्यूटी बारी-बारी करें और अंदर विश्राम लें','मैदानी कामाच्या पाळ्या बदला आणि आत विश्रांती घ्या'),
        ('pickup','Reduce waiting at the school gate','स्कूल के गेट पर इंतज़ार कम करें','शाळेच्या प्रवेशद्वारावरील प्रतीक्षा कमी करा')]:
        entries['headline.'+code]={'en':en,'hi':hi,'mr':mr}
    entries['review.classTeacher']={'en':'{0} teacher','hi':'{0} शिक्षक','mr':'{0} शिक्षक'}
    entries['class.label']={'en':'Class {0}','hi':'कक्षा {0}','mr':'वर्ग {0}'}
    return {'meta': {'en': {'locale':'en-IN','review':'reviewed source wording'},
                     'hi': {'locale':'hi-IN','review':'needs native review'},
                     'mr': {'locale':'mr-IN','review':'needs native review'}}, 'entries': entries}


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(ROOT))
    (ROOT / 'assets' / 'catalogue.json').write_text(json.dumps(build(), ensure_ascii=False, indent=2), encoding='utf-8')
