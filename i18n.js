const translations={
 hi:{'Guardian tools':'गार्डियन उपकरण','Today':'आज','Children':'बच्चे','Exposure':'संपर्क समय','Routes':'रास्ते','Classroom air':'कक्षा की हवा','Observations':'स्थानीय जानकारी','Alerts':'सूचनाएँ','School desk':'स्कूल प्रबंधन','Reports':'रिपोर्ट','Sign out':'साइन आउट','Refresh':'फिर जाँचें','My day':'मेरा दिन','School plan':'स्कूल की योजना','My activities':'मेरी गतिविधियाँ','Air explorer':'हवा की जानकारी','Read aloud':'पढ़कर सुनाएँ','See my school plan':'स्कूल की योजना देखें','Take it easy outside today.':'आज बाहर हल्की गतिविधियाँ करें।','Let’s plan some indoor activities.':'आज अंदर की गतिविधियों की योजना बनाएँ।','My little checklist':'मेरी छोटी सूची','What’s happening at school?':'स्कूल में क्या योजना है?','Your school-day planning flag':'आज के स्कूल का संकेत','What to review today':'आज क्या जाँचना है','Why?':'कारण क्या है?','Why this suggestion?':'यह सुझाव क्यों?','Compare route proxies':'रास्तों के अनुमान की तुलना करें','Save notification preferences':'सूचना विकल्प सहेजें','Acknowledge class plan':'कक्षा की योजना की पुष्टि करें','Class acknowledged':'कक्षा की पुष्टि हो गई','Publish school announcement':'स्कूल की सूचना जारी करें','Save child profile':'बच्चे की जानकारी सहेजें','Record exposure proxy':'संपर्क का अनुमान दर्ज करें','Share school observation':'स्कूल की जानकारी साझा करें','The next 24–48 hours':'अगले 24–48 घंटे','Enable browser notifications':'ब्राउज़र सूचनाएँ चालू करें'},
 mr:{'Guardian tools':'गार्डियन साधने','Today':'आज','Children':'मुले','Exposure':'संपर्क वेळ','Routes':'मार्ग','Classroom air':'वर्गातील हवा','Observations':'स्थानिक नोंदी','Alerts':'सूचना','School desk':'शाळा व्यवस्थापन','Reports':'अहवाल','Sign out':'साइन आउट','Refresh':'पुन्हा तपासा','My day':'माझा दिवस','School plan':'शाळेची योजना','My activities':'माझे उपक्रम','Air explorer':'हवेची माहिती','Read aloud':'वाचून दाखवा','See my school plan':'शाळेची योजना पाहा','Take it easy outside today.':'आज बाहेर हलके उपक्रम करा.','Let’s plan some indoor activities.':'आज वर्गातील उपक्रमांची योजना करूया.','My little checklist':'माझी छोटी यादी','What’s happening at school?':'शाळेत काय योजना आहे?','Your school-day planning flag':'आजचा शाळेचा संकेत','What to review today':'आज काय तपासायचे','Why?':'कारण काय?','Why this suggestion?':'हा सल्ला का?','Compare route proxies':'मार्गांच्या अंदाजांची तुलना करा','Save notification preferences':'सूचना पर्याय जतन करा','Acknowledge class plan':'वर्गाची योजना मान्य करा','Class acknowledged':'वर्गाची पुष्टी झाली','Publish school announcement':'शाळेची सूचना प्रकाशित करा','Save child profile':'मुलाची माहिती जतन करा','Record exposure proxy':'संपर्काचा अंदाज नोंदवा','Share school observation':'शाळेची नोंद सामायिक करा','The next 24–48 hours':'पुढील 24–48 तास','Enable browser notifications':'ब्राउझर सूचना सुरू करा'}
};
const adultPhrases=[
 ['Notification preferences','सूचना प्राथमिकताएँ','सूचना प्राधान्ये'],
 ['Message language','संदेश की भाषा','संदेशाची भाषा'],
 ['Quiet hours start','शांत समय शुरू','शांत वेळ सुरू'],
 ['Quiet hours end','शांत समय समाप्त','शांत वेळ समाप्त'],
 ['Daily cap','दैनिक सीमा','दैनिक मर्यादा'],
 ['School alerts','स्कूल सूचनाएँ','शाळेच्या सूचना'],
 ['Delivery history','भेजने का इतिहास','वितरण इतिहास'],
 ['Enable closed-browser Web Push','बंद ब्राउज़र के लिए वेब पुश चालू करें','बंद ब्राउझरसाठी वेब पुश सुरू करा'],
 ['Refresh Web Push subscription','वेब पुश सदस्यता फिर चालू करें','वेब पुश सदस्यता पुन्हा सुरू करा'],
 ['Pilot the indoor-PE routine','इनडोर खेल प्रक्रिया का पायलट','वर्गातील खेळ प्रक्रियेची चाचणी'],
 ['Routine','प्रक्रिया','प्रक्रिया'],
 ['Indoor PE','इनडोर खेल','वर्गातील खेळ'],
 ['Custom school notice','विशेष स्कूल सूचना','सानुकूल शाळा सूचना'],
 ['Staff instruction','कर्मचारी निर्देश','कर्मचारी सूचना'],
 ['Publish and start completion tracking','जारी करें और पूर्णता मापना शुरू करें','प्रकाशित करा आणि पूर्णता मोजणे सुरू करा'],
 ['Routine complete','प्रक्रिया पूरी हुई','प्रक्रिया पूर्ण'],
 ['Routine in progress','प्रक्रिया जारी है','प्रक्रिया सुरू आहे'],
 ['Teacher acknowledgment','शिक्षक की पुष्टि','शिक्षकांची पुष्टी'],
 ['Parent review','अभिभावक समीक्षा','पालकांचा आढावा'],
 ['Class action checklist','कक्षा कार्य सूची','वर्ग कृती सूची'],
 ['Read the latest school notice','स्कूल की नई सूचना पढ़ें','शाळेची नवीन सूचना वाचा'],
 ['Confirm the indoor PE space and supervision','इनडोर खेल की जगह और निगरानी की पुष्टि करें','वर्गातील खेळाची जागा आणि देखरेख निश्चित करा'],
 ['Tell the class what changes today','कक्षा को आज के बदलाव बताएँ','वर्गाला आजचे बदल सांगा'],
 ['Outdoor minutes moved indoors','अंदर किए गए बाहरी गतिविधि के मिनट','वर्गात हलवलेली मैदानी मिनिटे'],
 ['Latest published school notice','स्कूल की नवीनतम जारी सूचना','शाळेची नवीनतम प्रकाशित सूचना'],
 ['I reviewed this school plan','मैंने यह स्कूल योजना देख ली','मी ही शाळेची योजना पाहिली'],
 ['Plan reviewed','योजना देखी गई','योजनेचा आढावा झाला'],
 ['Credentials, sources and freshness','प्रमाण-पत्र, स्रोत और ताज़गी','प्रमाणपत्रे, स्रोत आणि ताजेपणा'],
 ['Nearby contributing points','पास के योगदान बिंदु','जवळचे योगदान बिंदू'],
 ['Held-out validation evidence','अलग रखे गए डेटा का सत्यापन','राखीव डेटाचे प्रमाणीकरण'],
 ['Sources and freshness','स्रोत और ताज़गी','स्रोत आणि ताजेपणा'],
 ['School history and weekly report','स्कूल इतिहास और साप्ताहिक रिपोर्ट','शाळेचा इतिहास आणि साप्ताहिक अहवाल'],
 ['Download weekly report','साप्ताहिक रिपोर्ट डाउनलोड करें','साप्ताहिक अहवाल डाउनलोड करा'],
 ['One school. One shared update.','एक स्कूल, एक साझा सूचना।','एक शाळा, एक सामायिक सूचना.'],
 ['What changes for the day?','आज क्या बदलेगा?','आज काय बदलेल?'],
 ['Workspace settings','कार्यस्थल सेटिंग','कार्यस्थान सेटिंग्ज'],
 ['What we collect and why','हम क्या लेते हैं और क्यों','आम्ही काय गोळा करतो आणि का']
];
const kidPhrases=[
 ['YOUR SCHOOL DAY','आपका स्कूल का दिन','तुमचा शाळेचा दिवस'],
 ['AIR EXPLORER','हवा के खोजी','हवेचा शोधक'],
 ['Assembly','सभा','प्रार्थना सभा'],['Break time','छुट्टी का समय','सुट्टीची वेळ'],['Sports','खेल','खेळ'],
 ['Classroom gathering','कक्षा में सभा','वर्गातील सभा'],['Short assembly','छोटी सभा','छोटी सभा'],
 ['Indoor games','अंदर के खेल','वर्गातील खेळ'],['Gentle play','हल्के खेल','हलके खेळ'],['Indoor movement','अंदर की गतिविधियाँ','वर्गातील हालचाली'],
 ['Check with your teacher','अपने शिक्षक से पूछें','शिक्षकांना विचारा'],
 ['Your teacher still needs to review this plan.','इस योजना को शिक्षक की समीक्षा चाहिए।','या योजनेचा शिक्षकांनी आढावा घ्यायचा आहे.'],
 ['Practice school plan confirmed','अभ्यास की स्कूल योजना की पुष्टि हुई','सरावाच्या शाळा योजनेची पुष्टी झाली'],
 ['School plan confirmed on this device','इस डिवाइस पर स्कूल योजना की पुष्टि हुई','या उपकरणावर शाळा योजनेची पुष्टी झाली'],
 ['Follow your teacher’s actual instructions. If you feel unwell, tell a trusted adult.','शिक्षक के असली निर्देश मानें। तबीयत खराब हो तो किसी भरोसेमंद बड़े को बताएँ।','शिक्षकांच्या खऱ्या सूचना पाळा. बरे वाटत नसेल तर विश्वासू मोठ्या व्यक्तीला सांगा.'],
 ['Your teacher may choose indoor games today. Check the school plan before going outside.','शिक्षक आज अंदर के खेल चुन सकते हैं। बाहर जाने से पहले स्कूल की योजना देखें।','शिक्षक आज वर्गातील खेळ निवडू शकतात. बाहेर जाण्यापूर्वी शाळेची योजना पाहा.'],
 ['Keep outdoor games gentle. Ask your teacher before a long or energetic sports session.','बाहर हल्के खेल खेलें। लंबे या तेज़ खेल से पहले शिक्षक से पूछें।','बाहेर हलके खेळ खेळा. लांब किंवा जोरदार खेळापूर्वी शिक्षकांना विचारा.'],
 ['The air update looks better. Ask your teacher about today’s activities.','हवा की जानकारी बेहतर दिख रही है। आज की गतिविधियों के बारे में शिक्षक से पूछें।','हवेची माहिती चांगली दिसते. आजच्या उपक्रमांबद्दल शिक्षकांना विचारा.'],
 ['We don’t have a current air update. Follow your teacher’s instructions.','हवा की नई जानकारी उपलब्ध नहीं है। शिक्षक के निर्देश मानें।','हवेची नवीन माहिती उपलब्ध नाही. शिक्षकांच्या सूचना पाळा.'],
 ['Check the plan, then enjoy your day.','योजना देखें, फिर दिन का आनंद लें।','योजना पाहा, मग दिवसाचा आनंद घ्या.'],
 ['Ask an adult to check the air.','हवा की जानकारी जाँचने के लिए बड़े से कहें।','हवेची माहिती तपासायला मोठ्यांना सांगा.'],
 ['Back to my day','मेरे दिन पर वापस जाएँ','माझ्या दिवसाकडे परत'],
 ['Tiny things can be in the air.','हवा में बहुत छोटे कण हो सकते हैं।','हवेत खूप छोटे कण असू शकतात.'],
 ['Air can contain tiny particles. We cannot always see them, but instruments can measure them.','हवा में छोटे कण हो सकते हैं। वे हमेशा दिखाई नहीं देते, लेकिन उपकरण उन्हें माप सकते हैं।','हवेत छोटे कण असू शकतात. ते नेहमी दिसत नाहीत, पण उपकरणे ते मोजू शकतात.'],
 ['An air-quality update helps your teacher decide what activities to plan.','हवा की जानकारी से शिक्षक गतिविधियों की योजना बना सकते हैं।','हवेची माहिती शिक्षकांना उपक्रम ठरवायला मदत करते.'],
 ['What are PM2.5 and PM10?','PM2.5 और PM10 क्या हैं?','PM2.5 आणि PM10 म्हणजे काय?'],
 ['These names describe particle sizes. PM2.5 particles are very small. PM10 includes slightly larger particles as well as the smaller ones.','ये नाम कणों का आकार बताते हैं। PM2.5 बहुत छोटे कण हैं। PM10 में छोटे और कुछ बड़े कण शामिल हैं।','ही नावे कणांचा आकार सांगतात. PM2.5 खूप छोटे कण आहेत. PM10 मध्ये छोटे आणि थोडे मोठे कणही असतात.'],
 ['What does an air-quality update help us do?','हवा की जानकारी किस काम में मदद करती है?','हवेची माहिती आपल्याला कशात मदत करते?'],
 ['Plan our outdoor activities','बाहर की गतिविधियों की योजना बनाना','मैदानी उपक्रम ठरवणे'],['Predict exam results','परीक्षा का परिणाम बताना','परीक्षेचा निकाल सांगणे'],['Choose a favourite colour','पसंदीदा रंग चुनना','आवडता रंग निवडणे'],
 ['An air update helps us and our teachers plan outdoor activities.','हवा की जानकारी हमें और शिक्षक को बाहर की गतिविधियाँ तय करने में मदद करती है।','हवेची माहिती आपल्याला आणि शिक्षकांना मैदानी उपक्रम ठरवायला मदत करते.'],
 ['Who should you check with before changing your school activity?','स्कूल की गतिविधि बदलने से पहले किससे पूछें?','शाळेचा उपक्रम बदलण्यापूर्वी कोणाला विचारावे?'],
 ['A teacher or trusted adult','शिक्षक या भरोसेमंद बड़े से','शिक्षक किंवा विश्वासू मोठ्या व्यक्तीला'],['A game character','खेल के पात्र से','खेळातील पात्राला'],['Nobody','किसी से नहीं','कोणालाही नाही'],
 ['A teacher or trusted adult can explain the school’s plan.','शिक्षक या भरोसेमंद बड़े स्कूल की योजना समझा सकते हैं।','शिक्षक किंवा विश्वासू मोठी व्यक्ती शाळेची योजना समजावू शकते.'],
 ['What is PM2.5?','PM2.5 क्या है?','PM2.5 म्हणजे काय?'],['A tiny particle in the air','हवा में बहुत छोटा कण','हवेतील खूप छोटा कण'],['A type of school bag','स्कूल बैग का प्रकार','दप्तराचा प्रकार'],['The time for lunch','खाने का समय','जेवणाची वेळ'],
 ['PM2.5 means very small particles. They are too small to see one by one.','PM2.5 बहुत छोटे कण होते हैं। वे इतने छोटे होते हैं कि एक-एक करके दिखाई नहीं देते।','PM2.5 खूप छोटे कण असतात. ते इतके छोटे असतात की एकेकटे दिसत नाहीत.'],
 ['That’s right!','सही जवाब!','बरोबर!'],['Let’s learn together.','चलो साथ सीखें।','चला एकत्र शिकूया.'],['Next question','अगला प्रश्न','पुढचा प्रश्न'],['Try the questions again','फिर से प्रश्न हल करें','प्रश्न पुन्हा सोडवा'],
 ['Pick an answer. It’s okay to learn as you go.','एक जवाब चुनें। कोशिश करते हुए सीखें।','एक उत्तर निवडा. प्रयत्न करत शिकूया.'],
 ['If you feel unwell, tell a teacher or another trusted adult. Keep following any care plan you already have.','तबीयत खराब हो तो शिक्षक या भरोसेमंद बड़े को बताएँ। अपनी मौजूदा देखभाल योजना मानते रहें।','बरे वाटत नसेल तर शिक्षक किंवा विश्वासू मोठ्या व्यक्तीला सांगा. तुमची आधीची काळजीची योजना पाळत राहा.']
];
for(const [en,hi,mr] of [...adultPhrases,...kidPhrases]){translations.hi[en]=hi;translations.mr[en]=mr}
export function getLanguage(){try{const saved=localStorage.getItem('airguardian.language');if(['en','hi','mr'].includes(saved))return saved}catch{}const match=document.cookie.match(/(?:^|; )airguardian_language=(en|hi|mr)(?:;|$)/);return match?.[1]||'en'}
export function setLanguage(lang){if(!['en','hi','mr'].includes(lang))return;document.documentElement.lang=lang;try{localStorage.setItem('airguardian.language',lang)}catch{}document.cookie=`airguardian_language=${lang}; Path=/; Max-Age=31536000; SameSite=Strict`}
export function translateUI(lang=getLanguage()){
 document.documentElement.lang=lang;
 if(lang==='en')return;
 const dictionary=translations[lang]||{};
 for(const element of document.querySelectorAll('.nav span,.guardian-tabs button,h1,h2,h3,button,summary,p,label,small,th,option,.kid-label,.kid-main b')){
  for(const node of element.childNodes)if(node.nodeType===Node.TEXT_NODE){const key=node.textContent.trim();if(dictionary[key])node.textContent=node.textContent.replace(key,dictionary[key]);else if(/^QUESTION [123] OF 3$/.test(key))node.textContent=(lang==='hi'?'प्रश्न ':'प्रश्न ')+key.match(/[123]/)[0]+' / 3'}
 }
}
