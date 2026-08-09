export type LocalizedText = { en: string; ru: string };

export type Source = {
  id: string;
  title: string;
  creator: string;
  url: string;
  sourceType: LocalizedText;
  originalLanguage: LocalizedText;
  languageCode: "en" | "ru" | "pt-BR" | "ko";
  captionBasis: LocalizedText;
};

export type Section = {
  id: string;
  title: LocalizedText;
  introduction: LocalizedText;
  imageId: string;
};

export type Question = {
  id: string;
  sectionId: string;
  construct: string;
  text: LocalizedText;
  sourceIds: string[];
  responseKind: "trait" | "retrospective" | "context";
  allowUnknown: boolean;
  allowNotApplicable: boolean;
  reviewedForDuplication: boolean;
  reviewedForDoubleBarrelled: boolean;
};

export type ImageCredit = {
  id: string;
  localPath: string;
  title: string;
  creator: string;
  license: string;
  sourceUrl: string;
  downloadUrl: string;
  alt: LocalizedText;
};

export type Reference = {
  name: string;
  url: string;
};

export type InstrumentReview = Reference & {
  included: boolean;
  reuseDecision: LocalizedText;
};

export const appCopy = {
  en: {
    ownerIntro: "I am already diagnosed with mild ASD and am taking this test for a video.",
    medicalNote:
      "This is not a diagnostic test. If it makes you curious, seek a professional assessment like I did.",
    resultDisclaimer:
      "This is an estimate of trait resonance, not a diagnosis. Diagnosis requires a qualified specialist.",
  },
  ru: {
    ownerIntro: "У меня уже диагностировано РАС лёгкой степени, и я прохожу этот тест для видео.",
    medicalNote:
      "Это не диагностический тест. Если результат вызовет у вас вопросы, обратитесь за профессиональной оценкой, как это в своё время сделал я.",
    resultDisclaimer:
      "Это приблизительная оценка того, насколько вам близки эти особенности, а не диагноз. Диагноз может поставить только квалифицированный специалист.",
  },
};

const english: LocalizedText = { en: "English", ru: "английский" };
const russian: LocalizedText = { en: "Russian", ru: "русский" };
const brazilianPortuguese: LocalizedText = {
  en: "Brazilian Portuguese",
  ru: "бразильский португальский",
};
const korean: LocalizedText = { en: "Korean", ru: "корейский" };

const creatorEnglishCaptions: LocalizedText = {
  en: "Creator-supplied English captions",
  ru: "английские субтитры, предоставленные автором",
};
const automaticEnglishCaptions: LocalizedText = {
  en: "English automatic captions",
  ru: "автоматические английские субтитры",
};
const englishCaptions: LocalizedText = {
  en: "English captions",
  ru: "английские субтитры",
};
const translatedRussianCaptions: LocalizedText = {
  en: "Manual Russian captions translated into English",
  ru: "ручные русские субтитры, переведённые на английский",
};
const translatedPortugueseCaptions: LocalizedText = {
  en: "Manual Brazilian Portuguese captions translated into English",
  ru: "ручные бразильские португальские субтитры, переведённые на английский",
};
const translatedKoreanCaptions: LocalizedText = {
  en: "Korean automatic captions translated into English",
  ru: "автоматические корейские субтитры, переведённые на английский",
};

export const sources: Source[] = [
  {
    id: "s01",
    title:
      "7 Signs of Autism in Men (DSM-5 Symptoms of Autism/Aspergers in High Functioning Autistic Adults)",
    creator: "Autism From The Inside",
    url: "https://www.youtube.com/watch?v=o8mhr1PcZ4Q",
    sourceType: {
      en: "Autistic creator's lived-experience explainer",
      ru: "объяснение на основе личного опыта аутичного автора",
    },
    originalLanguage: english,
    languageCode: "en",
    captionBasis: creatorEnglishCaptions,
  },
  {
    id: "s02",
    title: "7 Signs of Undiagnosed Autism in Adults",
    creator: "Autism From The Inside",
    url: "https://www.youtube.com/watch?v=qwu3iZSgf10",
    sourceType: {
      en: "Autistic creator's lived-experience explainer",
      ru: "объяснение на основе личного опыта аутичного автора",
    },
    originalLanguage: english,
    languageCode: "en",
    captionBasis: automaticEnglishCaptions,
  },
  {
    id: "s03",
    title: "Are You Autistic? 25 Questions To Ask Yourself! | Patron's Choice",
    creator: "Autism From The Inside",
    url: "https://www.youtube.com/watch?v=lXz9TpKGd5g",
    sourceType: {
      en: "Autistic creator's self-reflection list",
      ru: "список для самоанализа от аутичного автора",
    },
    originalLanguage: english,
    languageCode: "en",
    captionBasis: creatorEnglishCaptions,
  },
  {
    id: "s04",
    title:
      "63 common autistic traits you never realised were signs of autism! How many apply to you?",
    creator: "Autism From The Inside",
    url: "https://www.youtube.com/watch?v=FyoGpebQGYE",
    sourceType: {
      en: "Autistic creator's informal community-pattern list",
      ru: "неформальный список наблюдений аутичного сообщества от аутичного автора",
    },
    originalLanguage: english,
    languageCode: "en",
    captionBasis: creatorEnglishCaptions,
  },
  {
    id: "s05",
    title: "Spotting Autism in Adults - Common Signs and Traits of Autistic Adults",
    creator: "Orion Kelly - That Autistic Guy",
    url: "https://www.youtube.com/watch?v=HlEWIAiqSoc",
    sourceType: {
      en: "Autistic creator's first-person explainer",
      ru: "объяснение от первого лица аутичного автора",
    },
    originalLanguage: english,
    languageCode: "en",
    captionBasis: creatorEnglishCaptions,
  },
  {
    id: "s06",
    title: "20 Signs of Autism in Adults - Autistic Traits You Never Knew Existed",
    creator: "Orion Kelly - That Autistic Guy",
    url: "https://www.youtube.com/watch?v=rjiJebsPKyU",
    sourceType: {
      en: "Autistic creator's first-person list",
      ru: "список от первого лица аутичного автора",
    },
    originalLanguage: english,
    languageCode: "en",
    captionBasis: englishCaptions,
  },
  {
    id: "s07",
    title: "How to Spot Autism in High-Masking Adults",
    creator: "Auticate with Chris & Debby",
    url: "https://www.youtube.com/watch?v=jJDKjH6rHhw",
    sourceType: {
      en: "High-masking autistic creator's informal lived-experience list",
      ru: "неформальный список личного опыта аутичного автора с выраженным маскингом",
    },
    originalLanguage: english,
    languageCode: "en",
    captionBasis: creatorEnglishCaptions,
  },
  {
    id: "s08",
    title: '13 autism symptoms in adults (you\'re not just a "highly sensitive person/hsp")',
    creator: "Dr. Kim Sage, Licensed Psychologist",
    url: "https://www.youtube.com/watch?v=gd9V61tXacY",
    sourceType: {
      en: "Educational comparison by a licensed clinical psychologist",
      ru: "образовательное сравнение от лицензированного клинического психолога",
    },
    originalLanguage: english,
    languageCode: "en",
    captionBasis: automaticEnglishCaptions,
  },
  {
    id: "s09",
    title: "Autism diagnosis criteria: explained (DSM-5)",
    creator: "Yo Samdy Sam",
    url: "https://www.youtube.com/watch?v=1yva4RZW_s0",
    sourceType: {
      en: "Late-diagnosed autistic creator explaining diagnostic criteria",
      ru: "объяснение диагностических критериев от аутичного автора с поздним диагнозом",
    },
    originalLanguage: english,
    languageCode: "en",
    captionBasis: creatorEnglishCaptions,
  },
  {
    id: "s10",
    title: "How to spot autism in High Masking Autistic Women - What’s behind the mask?",
    creator: "Autism From The Inside",
    url: "https://www.youtube.com/watch?v=oYycpKcUhc4",
    sourceType: {
      en: "Autistic creator's conceptual guide to high masking",
      ru: "концептуальное руководство по выраженному маскингу от аутичного автора",
    },
    originalLanguage: english,
    languageCode: "en",
    captionBasis: creatorEnglishCaptions,
  },
  {
    id: "s11",
    title: "16 Overlooked Autistic Traits in Women",
    creator: "Mom on the Spectrum",
    url: "https://www.youtube.com/watch?v=xeZZHnQYoR4",
    sourceType: {
      en: "Late-diagnosed autistic woman's lived-experience and self-advocacy",
      ru: "личный опыт и самозащита аутичной женщины с поздним диагнозом",
    },
    originalLanguage: english,
    languageCode: "en",
    captionBasis: automaticEnglishCaptions,
  },
  {
    id: "s12",
    title: "Autism symptoms in GIRLS",
    creator: "Yo Samdy Sam",
    url: "https://www.youtube.com/watch?v=ixRSb00BplM",
    sourceType: {
      en: "Late-diagnosed autistic woman's lived-experience explainer",
      ru: "объяснение на основе личного опыта аутичной женщины с поздним диагнозом",
    },
    originalLanguage: english,
    languageCode: "en",
    captionBasis: {
      en: "Creator-supplied English (UK) captions",
      ru: "английские субтитры британского варианта, предоставленные автором",
    },
  },
  {
    id: "s13",
    title: "Behind the Mask: Autism for Women and Girls | Kate Kahle | TEDxAustinCollege",
    creator: "TEDx Talks",
    url: "https://www.youtube.com/watch?v=Tbes1mm2VgM",
    sourceType: {
      en: "Autistic woman's lived-experience TEDx talk",
      ru: "TEDx-выступление аутичной женщины о личном опыте",
    },
    originalLanguage: english,
    languageCode: "en",
    captionBasis: automaticEnglishCaptions,
  },
  {
    id: "s14",
    title: "Girls and Women and Autism: What’s the difference? - Sarah Hendrickx",
    creator: "NAS South Hampshire",
    url: "https://www.youtube.com/watch?v=yKzWbDPisNk",
    sourceType: {
      en: "Long-form lecture combining lived and professional experience",
      ru: "подробная лекция, объединяющая личный и профессиональный опыт",
    },
    originalLanguage: english,
    languageCode: "en",
    captionBasis: automaticEnglishCaptions,
  },
  {
    id: "s15",
    title: "how to spot high masking autism: 13 signs",
    creator: "Dr. Kim Sage, Licensed Psychologist",
    url: "https://www.youtube.com/watch?v=IqxTLPv0ox0",
    sourceType: {
      en: "Research-informed education by a licensed clinical psychologist",
      ru: "образовательный материал лицензированного клинического психолога с опорой на исследования",
    },
    originalLanguage: english,
    languageCode: "en",
    captionBasis: automaticEnglishCaptions,
  },
  {
    id: "s16",
    title: "How Adult Autism Goes Undetected",
    creator: "PBS Vitals",
    url: "https://www.youtube.com/watch?v=2rxzC4OBaOs",
    sourceType: {
      en: "Health journalism with an autistic educator and clinical psychologist",
      ru: "медицинская журналистика с участием аутичного просветителя и клинического психолога",
    },
    originalLanguage: english,
    languageCode: "en",
    captionBasis: creatorEnglishCaptions,
  },
  {
    id: "s17",
    title: "Signs and Symptoms of Autism",
    creator: "Doctor O'Donovan",
    url: "https://www.youtube.com/watch?v=_snimIOTp9o",
    sourceType: {
      en: "Physician health-education video based on clinical resources",
      ru: "медицинский образовательный материал врача на основе клинических источников",
    },
    originalLanguage: english,
    languageCode: "en",
    captionBasis: automaticEnglishCaptions,
  },
  {
    id: "s18",
    title: "What is Autism?",
    creator: "National Autistic Society",
    url: "https://www.youtube.com/watch?v=Lk4qs8jGN4U",
    sourceType: {
      en: "Official autism-charity explainer",
      ru: "официальный обзор благотворительной организации по вопросам аутизма",
    },
    originalLanguage: english,
    languageCode: "en",
    captionBasis: automaticEnglishCaptions,
  },
  {
    id: "s19",
    title: "What is Autism? | APA",
    creator: "American Psychiatric Association",
    url: "https://www.youtube.com/watch?v=MTW7H5UQ8Ts",
    sourceType: {
      en: "Official psychiatry professional-body explainer",
      ru: "официальный обзор профессиональной психиатрической организации",
    },
    originalLanguage: english,
    languageCode: "en",
    captionBasis: automaticEnglishCaptions,
  },
  {
    id: "s20",
    title: "Признаки #аутизма у взрослых [Signs of #Autism in Adults]",
    creator: "Ольга Ткалич [Olga Tkalich]",
    url: "https://www.youtube.com/watch?v=fqcGagcpxNI",
    sourceType: {
      en: "Autism-specialist psychologist's explainer",
      ru: "объяснение психолога — специалиста по аутизму",
    },
    originalLanguage: russian,
    languageCode: "ru",
    captionBasis: translatedRussianCaptions,
  },
  {
    id: "s21",
    title: "Ты не странная. Это может быть аутизм (РАС) [You are not strange. It may be autism (ASD)]",
    creator: "Ольга Ткалич [Olga Tkalich]",
    url: "https://www.youtube.com/watch?v=hn4tPhIGzAg",
    sourceType: {
      en: "Autism-specialist psychologist discussing presentations in women",
      ru: "психолог — специалист по аутизму рассказывает о проявлениях у женщин",
    },
    originalLanguage: russian,
    languageCode: "ru",
    captionBasis: translatedRussianCaptions,
  },
  {
    id: "s22",
    title:
      "Adultos com Autismo | Asperger - Saiba 10 sinais de autismo em adultos [Adults with Autism: 10 Signs in Adults]",
    creator: "Neuropsicóloga - Larissa Beatriz Cossalter",
    url: "https://www.youtube.com/watch?v=DdcVhPAXteo",
    sourceType: {
      en: "Licensed psychologist and neuropsychologist's explainer",
      ru: "объяснение лицензированного психолога и нейропсихолога",
    },
    originalLanguage: brazilianPortuguese,
    languageCode: "pt-BR",
    captionBasis: translatedPortugueseCaptions,
  },
  {
    id: "s23",
    title:
      "자폐? 자폐증?(X) 자폐스펙트럼장애!(O) 의심해야 하는 증상 4가지 [Autism Spectrum Disorder: Four Signs to Suspect]",
    creator: "Seoul National University Bundang Hospital",
    url: "https://www.youtube.com/watch?v=_kQu7cREqSk",
    sourceType: {
      en: "Official university-hospital video with a child psychiatry professor",
      ru: "официальное видео университетской больницы с профессором детской психиатрии",
    },
    originalLanguage: korean,
    languageCode: "ko",
    captionBasis: translatedKoreanCaptions,
  },
  {
    id: "s24",
    title: "Early Signs of Autism Video Tutorial | Kennedy Krieger Institute",
    creator: "Kennedy Krieger Institute",
    url: "https://www.youtube.com/watch?v=YtvP5A5OHpU",
    sourceType: {
      en: "Clinical tutorial by a specialist center director",
      ru: "клиническое руководство директора специализированного центра",
    },
    originalLanguage: english,
    languageCode: "en",
    captionBasis: creatorEnglishCaptions,
  },
  {
    id: "s25",
    title: "Kids at Play: Looking for Early Signs of Autism",
    creator: "University of Pennsylvania",
    url: "https://www.youtube.com/watch?v=34-yGI54sh4",
    sourceType: {
      en: "University research-news feature",
      ru: "университетский научно-популярный материал",
    },
    originalLanguage: english,
    languageCode: "en",
    captionBasis: automaticEnglishCaptions,
  },
  {
    id: "s26",
    title: "Signs of Autism in Children",
    creator: "Nicklaus Children's Hospital",
    url: "https://www.youtube.com/watch?v=FGTcXAgzxWw",
    sourceType: {
      en: "Children's-hospital explainer by a speech-language pathologist",
      ru: "обзор детской больницы от специалиста по речи и языку",
    },
    originalLanguage: english,
    languageCode: "en",
    captionBasis: automaticEnglishCaptions,
  },
  {
    id: "s27",
    title: "Signs of Autism in Children",
    creator: "Cleveland Clinic",
    url: "https://www.youtube.com/watch?v=zlkPVm-FRI0",
    sourceType: {
      en: "Hospital explainer with a pediatric clinician",
      ru: "обзор больницы с участием детского врача",
    },
    originalLanguage: english,
    languageCode: "en",
    captionBasis: creatorEnglishCaptions,
  },
  {
    id: "s28",
    title: "What are the signs of autism and how does it affect the child?",
    creator: "Hopebridge Autism Therapy Centers",
    url: "https://www.youtube.com/watch?v=PGwBWMN4-Po",
    sourceType: {
      en: "Commercial autism-service provider's explainer",
      ru: "обзор коммерческого поставщика услуг в сфере аутизма",
    },
    originalLanguage: english,
    languageCode: "en",
    captionBasis: automaticEnglishCaptions,
  },
  {
    id: "s29",
    title: "10 Subtle Signs Of Autism Most Parents Miss",
    creator: "Emma Hubbard",
    url: "https://www.youtube.com/watch?v=nD0_ICrtNvc",
    sourceType: {
      en: "Pediatric occupational therapist's developmental explainer",
      ru: "объяснение детского эрготерапевта по вопросам развития",
    },
    originalLanguage: english,
    languageCode: "en",
    captionBasis: creatorEnglishCaptions,
  },
  {
    id: "s30",
    title: "Is It Speech Delay or Autism? | Early Autism Signs in Toddlers",
    creator: "Dr. Mary Barbera - Turn Autism Around®",
    url: "https://www.youtube.com/watch?v=ifOeX3K1Jxk",
    sourceType: {
      en: "Registered nurse and behavior analyst's commercial education video",
      ru: "коммерческий образовательный материал медсестры и специалиста по анализу поведения",
    },
    originalLanguage: english,
    languageCode: "en",
    captionBasis: creatorEnglishCaptions,
  },
];
export const sections: Section[] = [
  {
    id: "conversation",
    title: { en: "Conversation flow", ru: "Ход разговора" },
    introduction: {
      en: "How I enter, pace, and process conversations.",
      ru: "Как я вступаю в разговор, поддерживаю его темп и осмысливаю смысл.",
    },
    imageId: "hokusai-wave",
  },
  {
    id: "context-nonverbal",
    title: { en: "Context and nonverbal meaning", ru: "Контекст и невербальный смысл" },
    introduction: {
      en: "How I understand indirect language, expressions, voice, and eye contact.",
      ru: "Как я понимаю непрямую речь, мимику, голос и зрительный контакт.",
    },
    imageId: "wheat-field",
  },
  {
    id: "relationships",
    title: { en: "Relationships and social energy", ru: "Отношения и социальная энергия" },
    introduction: {
      en: "How relationships and social events affect me.",
      ru: "Как на меня влияют отношения и социальные мероприятия.",
    },
    imageId: "oxbow",
  },
  {
    id: "masking",
    title: { en: "Masking and compensation", ru: "Маскинг и компенсация" },
    introduction: {
      en: "What I consciously change or hide when I am with other people.",
      ru: "Что я сознательно меняю или скрываю в присутствии других людей.",
    },
    imageId: "irises",
  },
  {
    id: "repetition",
    title: { en: "Repetition and regulation", ru: "Повторение и саморегуляция" },
    introduction: {
      en: "How repetition helps me and how interruption affects me.",
      ru: "Как повторение помогает мне и как на меня влияет его прерывание.",
    },
    imageId: "bamboo-window",
  },
  {
    id: "routine-interests",
    title: { en: "Routine, attention, and interests", ru: "Распорядок, внимание и интересы" },
    introduction: {
      en: "How predictability, transitions, details, and strong interests work for me.",
      ru: "Как для меня работают предсказуемость, переходы, детали и сильные интересы.",
    },
    imageId: "water-pitcher",
  },
  {
    id: "sensory-body",
    title: { en: "Sensory and body awareness", ru: "Сенсорные ощущения и сигналы тела" },
    introduction: {
      en: "How I experience sound, light, texture, busy places, and body signals.",
      ru: "Как я воспринимаю звук, свет, текстуру, насыщенные места и сигналы тела.",
    },
    imageId: "le-gray-wave",
  },
  {
    id: "daily-regulation",
    title: { en: "Daily demands and regulation", ru: "Повседневная нагрузка и регуляция" },
    introduction: {
      en: "How demands, interruptions, overload, and emotions affect my capacity.",
      ru: "Как требования, прерывания, перегрузка и эмоции влияют на мои возможности.",
    },
    imageId: "old-trees",
  },
  {
    id: "childhood",
    title: { en: "Before age 12", ru: "До 12 лет" },
    introduction: {
      en: "What I remember, or was told, about my childhood development and play.",
      ru: "Что я помню или знаю со слов других о своём детском развитии и игре.",
    },
    imageId: "calm-sea",
  },
  {
    id: "context-impact",
    title: { en: "Context and daily impact", ru: "Контекст и влияние на повседневную жизнь" },
    introduction: {
      en: "Where these patterns appear and how they affect my life.",
      ru: "Где проявляются эти особенности и как они влияют на мою жизнь.",
    },
    imageId: "moonrise",
  },
];

const makeQuestion = (
  id: string,
  sectionId: string,
  construct: string,
  en: string,
  ru: string,
  sourceIds: string[],
  responseKind: Question["responseKind"] = "trait",
): Question => {
  const retrospective = responseKind === "retrospective";
  return {
    id,
    sectionId,
    construct,
    text: { en, ru },
    sourceIds,
    responseKind,
    allowUnknown: retrospective,
    allowNotApplicable: retrospective,
    reviewedForDuplication: true,
    reviewedForDoubleBarrelled: true,
  };
};

export const questions: Question[] = [
  makeQuestion(
    "q01",
    "conversation",
    "conscious-social-rule-analysis",
    "I consciously analyze social rules that other people seem to follow automatically.",
    "Я сознательно анализирую социальные правила, которым другие люди, кажется, следуют автоматически.",
    ["s02", "s08", "s16"],
  ),
  makeQuestion(
    "q02",
    "conversation",
    "group-conversation-entry",
    "I find it difficult to enter a group conversation at the right moment.",
    "Мне трудно вступить в групповой разговор в подходящий момент.",
    ["s04", "s22"],
  ),
  makeQuestion(
    "q03",
    "conversation",
    "knowing-when-to-stop-talking",
    "I find it difficult to know when to stop talking.",
    "Мне трудно понять, когда пора перестать говорить.",
    ["s01", "s22"],
  ),
  makeQuestion(
    "q04",
    "conversation",
    "delayed-conversation-meaning",
    "I understand the intended meaning of a conversation only later.",
    "Я понимаю подразумеваемый смысл разговора лишь позже.",
    ["s05", "s07"],
  ),
  makeQuestion(
    "q05",
    "context-nonverbal",
    "literal-language-interpretation",
    "I tend to understand words literally when the speaker means something else.",
    "Я склонен воспринимать слова буквально, когда говорящий подразумевает что-то другое.",
    ["s09", "s17", "s22"],
  ),
  makeQuestion(
    "q06",
    "context-nonverbal",
    "unstated-meaning-inference",
    "I find it difficult to understand a meaning that is not stated directly.",
    "Мне трудно понять смысл, если он не выражен прямо.",
    ["s08", "s20", "s22"],
  ),
  makeQuestion(
    "q07",
    "context-nonverbal",
    "facial-emotion-inference",
    "I find it difficult to infer another person's feelings from their facial expression.",
    "Мне трудно понять чувства другого человека по выражению его лица.",
    ["s09", "s20", "s22"],
  ),
  makeQuestion(
    "q08",
    "context-nonverbal",
    "vocal-tone-inference",
    "I find it difficult to infer a speaker's meaning from their tone of voice.",
    "Мне трудно понять намерение говорящего по тону его голоса.",
    ["s01", "s05", "s22"],
  ),
  makeQuestion(
    "q09",
    "context-nonverbal",
    "eye-contact-listening-interference",
    "Eye contact makes it harder for me to focus on what another person is saying.",
    "Зрительный контакт мешает мне сосредоточиться на словах собеседника.",
    ["s09", "s16"],
  ),
  makeQuestion(
    "q10",
    "relationships",
    "maintaining-close-relationships",
    "I find it difficult to maintain close relationships.",
    "Мне трудно поддерживать близкие отношения.",
    ["s09", "s21", "s23"],
  ),
  makeQuestion(
    "q11",
    "relationships",
    "unstructured-group-difficulty",
    "Unstructured group socializing is harder for me than one-to-one conversation.",
    "Неструктурированное общение в группе даётся мне труднее, чем разговор один на один.",
    ["s11", "s14"],
  ),
  makeQuestion(
    "q12",
    "relationships",
    "group-event-avoidance",
    "I avoid group events because they feel overwhelming.",
    "Я избегаю мероприятий с группой людей, потому что они меня перегружают.",
    ["s08", "s11", "s15"],
  ),
  makeQuestion(
    "q13",
    "relationships",
    "social-recovery-solitude",
    "After a social event, I need a long time alone to recover.",
    "После социального мероприятия мне нужно надолго остаться в одиночестве, чтобы восстановиться.",
    ["s06", "s14", "s15"],
  ),
  makeQuestion(
    "q14",
    "masking",
    "copied-social-style",
    "I copy another person's social style to fit in.",
    "Я копирую манеру общения другого человека, чтобы не выделяться.",
    ["s11", "s14", "s21"],
  ),
  makeQuestion(
    "q15",
    "masking",
    "prepared-conversation-phrases",
    "I prepare exact phrases before a conversation.",
    "Я заранее готовлю точные фразы для разговора.",
    ["s06", "s13", "s15"],
  ),
  makeQuestion(
    "q16",
    "masking",
    "managed-eye-contact",
    "I consciously manage my eye contact during social interaction.",
    "Я сознательно контролирую зрительный контакт во время общения.",
    ["s08", "s13", "s21"],
  ),
  makeQuestion(
    "q17",
    "masking",
    "hidden-repetitive-behavior",
    "I hide repetitive behavior around other people.",
    "Я скрываю повторяющееся поведение в присутствии других людей.",
    ["s03", "s12", "s15"],
  ),
  makeQuestion(
    "q18",
    "masking",
    "hidden-sensory-distress",
    "I hide sensory distress so that other people do not notice it.",
    "Я скрываю сильный сенсорный дискомфорт, чтобы другие люди его не заметили.",
    ["s10", "s15"],
  ),
  makeQuestion(
    "q19",
    "masking",
    "public-private-capacity-gap",
    "I appear capable in public but lose much of that capacity in private.",
    "На людях кажется, что я хорошо справляюсь, но наедине мои возможности резко снижаются.",
    ["s10", "s14", "s15"],
  ),
  makeQuestion(
    "q20",
    "repetition",
    "repetition-for-regulation",
    "Repetitive behavior helps me regulate my state.",
    "Повторяющееся поведение помогает мне регулировать своё состояние.",
    ["s01", "s08", "s18"],
  ),
  makeQuestion(
    "q21",
    "repetition",
    "repeated-familiar-media",
    "I return repeatedly to the same familiar music or videos.",
    "Я снова и снова возвращаюсь к одной и той же знакомой музыке или видео.",
    ["s04", "s08"],
  ),
  makeQuestion(
    "q22",
    "repetition",
    "distress-at-repetition-interruption",
    "I become distressed when someone interrupts a repetitive activity.",
    "Я испытываю сильный дискомфорт, когда кто-то прерывает моё повторяющееся занятие.",
    ["s21", "s26"],
  ),
  makeQuestion(
    "q23",
    "routine-interests",
    "predictable-routine-need",
    "A predictable routine feels necessary for me to function.",
    "Предсказуемый распорядок кажется мне необходимым, чтобы справляться с повседневной жизнью.",
    ["s01", "s08", "s18"],
  ),
  makeQuestion(
    "q24",
    "routine-interests",
    "distress-at-small-change",
    "A small unexpected change can cause me intense emotional distress.",
    "Небольшое неожиданное изменение может вызвать у меня сильное эмоциональное напряжение.",
    ["s09", "s18", "s20"],
  ),
  makeQuestion(
    "q25",
    "routine-interests",
    "advance-planning-for-unfamiliarity",
    "I plan an unfamiliar place or event in exact detail before going.",
    "Перед посещением незнакомого места или мероприятия я подробно всё планирую.",
    ["s03", "s08", "s22"],
  ),
  makeQuestion(
    "q26",
    "routine-interests",
    "task-switching-difficulty",
    "I find it difficult to switch from one task to another.",
    "Мне трудно переключаться с одной задачи на другую.",
    ["s01", "s05", "s09"],
  ),
  makeQuestion(
    "q27",
    "routine-interests",
    "fixed-method-for-daily-tasks",
    "I need to do everyday tasks using my fixed method.",
    "Мне нужно выполнять повседневные задачи своим неизменным способом.",
    ["s02", "s07", "s20"],
  ),
  makeQuestion(
    "q28",
    "routine-interests",
    "absorbing-strong-interest",
    "I have an interest that absorbs much of my attention.",
    "У меня есть интерес, который поглощает значительную часть моего внимания.",
    ["s09", "s19", "s22"],
  ),
  makeQuestion(
    "q29",
    "routine-interests",
    "systemized-interest-information",
    "I organize information about a strong interest into detailed systems.",
    "Я организую сведения о своём сильном интересе в подробную систему.",
    ["s11", "s12", "s14"],
  ),
  makeQuestion(
    "q30",
    "routine-interests",
    "detail-first-attention",
    "I notice small details before I understand the overall context.",
    "Я замечаю мелкие детали раньше, чем понимаю общий контекст.",
    ["s07", "s08", "s14"],
  ),
  makeQuestion(
    "q31",
    "sensory-body",
    "painfully-intense-sound",
    "Ordinary sounds can feel painfully intense to me.",
    "Обычные звуки могут казаться мне болезненно громкими.",
    ["s06", "s17", "s18"],
  ),
  makeQuestion(
    "q32",
    "sensory-body",
    "overwhelming-bright-light",
    "Bright or fluorescent light overwhelms me.",
    "Яркий или флуоресцентный свет меня перегружает.",
    ["s01", "s18", "s19"],
  ),
  makeQuestion(
    "q33",
    "sensory-body",
    "intolerable-clothing-texture",
    "Clothing seams, tags, or some fabrics feel intolerable to me.",
    "Швы, ярлыки или некоторые ткани ощущаются для меня невыносимо.",
    ["s04", "s06", "s14"],
  ),
  makeQuestion(
    "q34",
    "sensory-body",
    "food-texture-restriction",
    "Food texture can make some foods impossible for me to eat.",
    "Из-за текстуры некоторые продукты становятся для меня несъедобными.",
    ["s06", "s22", "s28"],
  ),
  makeQuestion(
    "q35",
    "sensory-body",
    "busy-place-sensory-overload",
    "Busy places cause me sensory overload.",
    "Людные и насыщенные стимулами места вызывают у меня сенсорную перегрузку.",
    ["s01", "s16", "s21"],
  ),
  makeQuestion(
    "q36",
    "sensory-body",
    "late-body-signal-awareness",
    "I notice body signals such as hunger only when they become strong.",
    "Я замечаю сигналы тела, например голод, только когда они становятся сильными.",
    ["s04", "s05", "s21"],
  ),
  makeQuestion(
    "q37",
    "sensory-body",
    "strong-sensory-input-seeking",
    "I seek strong sensory input to regulate my state.",
    "Я ищу сильные сенсорные ощущения, чтобы регулировать своё состояние.",
    ["s02", "s08", "s09"],
  ),
  makeQuestion(
    "q38",
    "daily-regulation",
    "simultaneous-demand-overload",
    "Several simultaneous demands quickly overwhelm me.",
    "Несколько одновременных требований быстро меня перегружают.",
    ["s04", "s08", "s16"],
  ),
  makeQuestion(
    "q39",
    "daily-regulation",
    "variable-planning-capacity",
    "My ability to plan and organize changes sharply between situations.",
    "Моя способность планировать и организовывать резко меняется в разных ситуациях.",
    ["s02", "s10", "s12"],
  ),
  makeQuestion(
    "q40",
    "daily-regulation",
    "task-resumption-after-interruption",
    "After an interruption, I find it difficult to return to a task.",
    "После прерывания мне трудно вернуться к задаче.",
    ["s02", "s05", "s07"],
  ),
  makeQuestion(
    "q41",
    "daily-regulation",
    "communication-loss-during-overload",
    "During overload, my ability to communicate can disappear.",
    "Во время перегрузки у меня может исчезнуть способность общаться.",
    ["s02", "s14", "s18"],
  ),
  makeQuestion(
    "q42",
    "daily-regulation",
    "own-emotion-identification",
    "I find it difficult to identify my own emotions.",
    "Мне трудно распознавать собственные эмоции.",
    ["s04", "s20", "s22"],
  ),
  makeQuestion(
    "q43",
    "daily-regulation",
    "prolonged-emotional-absorption",
    "Another person's emotional state can affect my own state for hours.",
    "Эмоциональное состояние другого человека может влиять на моё состояние часами.",
    ["s03", "s07", "s13"],
  ),
  makeQuestion(
    "q44",
    "childhood",
    "childhood-difference-from-peers",
    "Before age 12, I often felt different from other children.",
    "До 12 лет у меня часто было ощущение, что я отличаюсь от других детей.",
    ["s03", "s12", "s15"],
    "retrospective",
  ),
  makeQuestion(
    "q45",
    "childhood",
    "childhood-solitary-play-preference",
    "Before age 12, I usually preferred to play alone.",
    "До 12 лет мне обычно больше нравилось играть в одиночку.",
    ["s09", "s21", "s28"],
    "retrospective",
  ),
  makeQuestion(
    "q46",
    "childhood",
    "childhood-object-sharing",
    "Before age 12, I rarely showed objects only to share my interest.",
    "До 12 лет показывать другим предметы только для того, чтобы поделиться интересом, было для меня редкостью.",
    ["s23", "s24", "s29"],
    "retrospective",
  ),
  makeQuestion(
    "q47",
    "childhood",
    "childhood-pretend-play",
    "Before age 12, pretend play was difficult for me.",
    "До 12 лет мне было трудно играть «понарошку».",
    ["s24", "s28", "s30"],
    "retrospective",
  ),
  makeQuestion(
    "q48",
    "childhood",
    "childhood-fixed-play-pattern",
    "Before age 12, my play often followed the same fixed pattern.",
    "До 12 лет моя игра часто следовала одному и тому же неизменному сценарию.",
    ["s21", "s26", "s29"],
    "retrospective",
  ),
  makeQuestion(
    "q49",
    "context-impact",
    "pattern-across-settings",
    "These patterns have appeared in more than one setting in my life.",
    "Эти особенности проявлялись более чем в одной обстановке моей жизни.",
    ["s02", "s09"],
    "context",
  ),
  makeQuestion(
    "q50",
    "context-impact",
    "meaningful-daily-impact",
    "These patterns have caused meaningful difficulty in my daily life.",
    "Эти особенности создавали заметные трудности в моей повседневной жизни.",
    ["s09", "s16"],
    "context",
  ),
];
export const imageCredits: ImageCredit[] = [
  {
    id: "hokusai-wave",
    localPath: "/images/hokusai-wave.webp",
    title: "Under the Wave off Kanagawa (The Great Wave)",
    creator: "Katsushika Hokusai",
    license: "CC0 1.0",
    sourceUrl: "https://www.metmuseum.org/art/collection/search/56353",
    downloadUrl: "https://images.metmuseum.org/CRDImages/as/original/DP141067.jpg",
    alt: {
      en: "A large blue wave curls above boats near Mount Fuji.",
      ru: "Большая синяя волна нависает над лодками у горы Фудзи.",
    },
  },
  {
    id: "wheat-field",
    localPath: "/images/wheat-field.webp",
    title: "Wheat Field with Cypresses",
    creator: "Vincent van Gogh",
    license: "CC0 1.0",
    sourceUrl: "https://www.metmuseum.org/art/collection/search/436535",
    downloadUrl: "https://images.metmuseum.org/CRDImages/ep/original/DP-42549-001.jpg",
    alt: {
      en: "A green wheat field and tall cypresses beneath a swirling sky.",
      ru: "Зелёное пшеничное поле и высокие кипарисы под вихревым небом.",
    },
  },
  {
    id: "oxbow",
    localPath: "/images/oxbow.webp",
    title: "View from Mount Holyoke, Northampton, Massachusetts, after a Thunderstorm—The Oxbow",
    creator: "Thomas Cole",
    license: "CC0 1.0",
    sourceUrl: "https://www.metmuseum.org/art/collection/search/10497",
    downloadUrl: "https://images.metmuseum.org/CRDImages/ad/original/DP-12550-001.jpg",
    alt: {
      en: "A wide river bends through a valley beneath a clearing storm.",
      ru: "Широкая река изгибается в долине под уходящей грозой.",
    },
  },
  {
    id: "irises",
    localPath: "/images/irises.webp",
    title: "Irises",
    creator: "Vincent van Gogh",
    license: "CC0 1.0",
    sourceUrl: "https://www.metmuseum.org/art/collection/search/436528",
    downloadUrl: "https://images.metmuseum.org/CRDImages/ep/original/DP346474.jpg",
    alt: {
      en: "A bouquet of purple irises stands in a pale vase.",
      ru: "Букет фиолетовых ирисов стоит в светлой вазе.",
    },
  },
  {
    id: "bamboo-window",
    localPath: "/images/bamboo-window.webp",
    title: "Window onto Bamboo on a Rainy Day",
    creator: "Gion Nankai",
    license: "CC0 1.0",
    sourceUrl: "https://www.metmuseum.org/art/collection/search/53450",
    downloadUrl: "https://images.metmuseum.org/CRDImages/as/original/DP-10807-115.jpg",
    alt: {
      en: "Dark bamboo leaves appear through a window on a rainy day.",
      ru: "Тёмные листья бамбука видны через окно в дождливый день.",
    },
  },
  {
    id: "water-pitcher",
    localPath: "/images/water-pitcher.webp",
    title: "Young Woman with a Water Pitcher",
    creator: "Johannes Vermeer",
    license: "CC0 1.0",
    sourceUrl: "https://www.metmuseum.org/art/collection/search/437881",
    downloadUrl: "https://images.metmuseum.org/CRDImages/ep/original/DP353257.jpg",
    alt: {
      en: "A young woman stands beside a table with a silver water pitcher.",
      ru: "Молодая женщина стоит у стола с серебряным кувшином для воды.",
    },
  },
  {
    id: "le-gray-wave",
    localPath: "/images/le-gray-wave.webp",
    title: "The Great Wave, Sète",
    creator: "Gustave Le Gray",
    license: "CC0 1.0",
    sourceUrl: "https://www.metmuseum.org/art/collection/search/261941",
    downloadUrl: "https://images.metmuseum.org/CRDImages/ph/original/DP223650.jpg",
    alt: {
      en: "A sea wave breaks beneath a bright, clouded sky.",
      ru: "Морская волна разбивается под светлым облачным небом.",
    },
  },
  {
    id: "old-trees",
    localPath: "/images/old-trees.webp",
    title: "Old Trees, Level Distance",
    creator: "Guo Xi",
    license: "CC0 1.0",
    sourceUrl: "https://www.metmuseum.org/art/collection/search/39668",
    downloadUrl: "https://images.metmuseum.org/CRDImages/as/original/DP167812_CRD.jpg",
    alt: {
      en: "Ancient trees spread over a level riverside landscape.",
      ru: "Старые деревья раскинулись над ровным речным пейзажем.",
    },
  },
  {
    id: "calm-sea",
    localPath: "/images/calm-sea.webp",
    title: "The Calm Sea",
    creator: "Gustave Courbet",
    license: "CC0 1.0",
    sourceUrl: "https://www.metmuseum.org/art/collection/search/436005",
    downloadUrl: "https://images.metmuseum.org/CRDImages/ep/original/DT1973.jpg",
    alt: {
      en: "A calm sea and pale sky meet beside a rocky shore.",
      ru: "Спокойное море и светлое небо сходятся у каменистого берега.",
    },
  },
  {
    id: "moonrise",
    localPath: "/images/moonrise.webp",
    title: "Moonrise",
    creator: "Henri-Joseph Harpignies",
    license: "CC0 1.0",
    sourceUrl: "https://www.metmuseum.org/art/collection/search/436632",
    downloadUrl: "https://images.metmuseum.org/CRDImages/ep/original/DP238263.jpg",
    alt: {
      en: "The moon rises over a quiet river landscape.",
      ru: "Луна восходит над тихим речным пейзажем.",
    },
  },
];

export const officialGuidance: Reference[] = [
  {
    name: "American Psychiatric Association — Autism Spectrum Disorder",
    url: "https://www.psychiatry.org/File%20Library/Psychiatrists/Practice/DSM/APA_DSM-5-Autism-Spectrum-Disorder.pdf",
  },
  {
    name: "NICE CG142 — Autism spectrum disorder in adults: diagnosis and management",
    url: "https://www.nice.org.uk/guidance/cg142/chapter/Recommendations",
  },
  {
    name: "WHO — Clinical descriptions and diagnostic requirements for ICD-11 mental, behavioural and neurodevelopmental disorders",
    url: "https://www.who.int/publications/i/item/9789240077263",
  },
  {
    name: "Hull et al. — Putting on My Best Normal: Social Camouflaging in Adults with Autism Spectrum Conditions",
    url: "https://discovery.ucl.ac.uk/1558346/",
  },
  {
    name: "Hull et al. — Development and Validation of the Camouflaging Autistic Traits Questionnaire",
    url: "https://link.springer.com/article/10.1007/s10803-018-3792-6",
  },
  {
    name: "Barrett et al. — The Adult Repetitive Behaviours Questionnaire-3",
    url: "https://link.springer.com/article/10.1186/s13229-024-00603-7",
  },
  {
    name: "Cambridge Autism Research Centre — Sensory Perception Quotient",
    url: "https://www.autismresearchcentre.com/tests/sensory-perception-quotient/",
  },
  {
    name: "WHO Disability Assessment Schedule 2.0",
    url: "https://www.who.int/standards/classifications/international-classification-of-functioning-disability-and-health/who-disability-assessment-schedule",
  },
];

export const instrumentReviews: InstrumentReview[] = [
  {
    name: "Camouflaging Autistic Traits Questionnaire (CAT-Q)",
    url: "https://link.springer.com/article/10.1007/s10803-018-3792-6",
    included: false,
    reuseDecision: {
      en: "Kept separate. Reuse requires attribution and license compliance; modified wording needs new validation.",
      ru: "Оставлен отдельно. Повторное использование требует атрибуции и соблюдения лицензии; изменённые формулировки требуют новой валидации.",
    },
  },
  {
    name: "Adult Repetitive Behaviours Questionnaire-3 (RBQ-3)",
    url: "https://www.cardiff.ac.uk/psychology/research/impact/measuring-repetitive-behaviours-across-the-lifespan",
    included: false,
    reuseDecision: {
      en: "Kept separate because the standalone form has no clear public redistribution or adaptation license.",
      ru: "Оставлен отдельно, поскольку для самостоятельной формы нет ясной публичной лицензии на распространение или адаптацию.",
    },
  },
  {
    name: "Autism Spectrum Quotient — Adult (AQ)",
    url: "https://www.autismresearchcentre.com/tests/autism-spectrum-quotient-aq-adult/",
    included: false,
    reuseDecision: {
      en: "Kept separate because reuse terms limit adaptation and distinguish noncommercial from commercial use.",
      ru: "Оставлен отдельно, поскольку условия ограничивают адаптацию и различают некоммерческое и коммерческое использование.",
    },
  },
  {
    name: "Sensory Perception Quotient — Adult (SPQ)",
    url: "https://www.autismresearchcentre.com/tests/sensory-perception-quotient/",
    included: false,
    reuseDecision: {
      en: "Kept separate because adaptation, translation, and commercial use require permission.",
      ru: "Оставлен отдельно, поскольку адаптация, перевод и коммерческое использование требуют разрешения.",
    },
  },
  {
    name: "Ritvo Autism Asperger Diagnostic Scale-Revised (RAADS-R)",
    url: "https://link.springer.com/article/10.1007/s10803-010-1133-5",
    included: false,
    reuseDecision: {
      en: "Kept separate because the primary paper describes clinician-supported use, not an unsupervised web form.",
      ru: "Оставлен отдельно, поскольку первичная публикация описывает применение при участии специалиста, а не самостоятельную веб-форму.",
    },
  },
  {
    name: "Social Responsiveness Scale, Second Edition — Adult Self-Report (SRS-2)",
    url: "https://www.wpspublish.com/srs-2-social-responsiveness-scale-second-edition",
    included: false,
    reuseDecision: {
      en: "Kept separate because its forms and digital administration are proprietary and licensed.",
      ru: "Оставлен отдельно, поскольку формы и цифровое проведение являются проприетарными и лицензируемыми.",
    },
  },
  {
    name: "Adolescent/Adult Sensory Profile",
    url: "https://www.pearsonassessments.com/en-us/Store/Professional-Assessments/Motor-Sensory/Adolescent-Adult-Sensory-Profile/p/100000434",
    included: false,
    reuseDecision: {
      en: "Kept separate because Pearson's forms and manual are proprietary.",
      ru: "Оставлен отдельно, поскольку формы и руководство Pearson являются проприетарными.",
    },
  },
  {
    name: "Glasgow Sensory Questionnaire",
    url: "https://link.springer.com/article/10.1007/s10803-012-1608-7",
    included: false,
    reuseDecision: {
      en: "Kept separate because no broad open license for public reuse or adaptation was identified.",
      ru: "Оставлен отдельно, поскольку не найдена широкая открытая лицензия на публичное использование или адаптацию.",
    },
  },
  {
    name: "WHO Disability Assessment Schedule 2.0 (WHODAS 2.0)",
    url: "https://www.who.int/standards/classifications/international-classification-of-functioning-disability-and-health/who-disability-assessment-schedule",
    included: false,
    reuseDecision: {
      en: "Kept separate because electronic capture, reproduction, or integration requires WHO licensing review.",
      ru: "Оставлен отдельно, поскольку электронный сбор, воспроизведение или интеграция требуют лицензионной проверки WHO.",
    },
  },
];
