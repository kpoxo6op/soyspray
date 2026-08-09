import { ArrowLeft, ArrowRight, ExternalLink, RotateCcw } from "lucide-react";
import {
  type Dispatch,
  type FormEvent,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
} from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { RadioGroup, RadioOption } from "@/components/ui/radio-group";
import {
  appCopy,
  imageCredits,
  instrumentReviews,
  officialGuidance,
  questions,
  sections,
  sources,
  type Question,
} from "@/data";
import {
  DOMAIN_WEIGHTS,
  canReveal,
  markerPercent,
  scoreAssessment,
  type Answer,
} from "@/lib/scoring";
import {
  reduceAssessmentState,
  resolveTheme,
  restoreState,
  serializeState,
  type AssessmentAction,
  type AssessmentState,
  type Language,
  type ThemePreference,
} from "@/lib/state";
import { uiCopy } from "@/ui-copy";

const STORAGE_KEY = "autism-traits-assessment:v1";

type Route =
  | { page: "intro" }
  | { page: "sources" }
  | { page: "assessment"; sectionId: string }
  | { page: "complete" }
  | { page: "result" };

const parseRoute = (): Route => {
  const path = window.location.hash.replace(/^#\/?/, "");
  if (path === "sources") return { page: "sources" };
  if (path === "complete") return { page: "complete" };
  if (path === "result") return { page: "result" };
  if (path.startsWith("assessment/")) {
    return { page: "assessment", sectionId: path.slice("assessment/".length) };
  }
  return { page: "intro" };
};

const navigate = (path: string, replace = false) => {
  const hash = `#${path}`;
  if (replace) {
    window.history.replaceState(null, "", hash);
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  } else {
    window.location.hash = path;
  }
};

const isCompleteAnswer = (question: Question, answer: Answer | undefined) =>
  typeof answer === "number" ||
  (question.responseKind === "retrospective" &&
    ((question.allowUnknown && answer === "unknown") ||
      (question.allowNotApplicable && answer === "not-applicable")));

const responseValue = (value: string): Answer => {
  if (value === "unknown" || value === "not-applicable") return value;
  return Number(value) as Answer;
};

const firstIncompleteSection = (answers: Record<string, Answer>) =>
  sections.find((section) =>
    questions
      .filter((question) => question.sectionId === section.id)
      .some((question) => !isCompleteAnswer(question, answers[question.id])),
  )?.id;

type SharedPageProps = {
  language: Language;
  state: AssessmentState;
  dispatch: Dispatch<AssessmentAction>;
};

const Header = ({ language, state, dispatch }: SharedPageProps) => {
  const copy = uiCopy[language];
  const [confirming, setConfirming] = useState(false);
  const hasProgress = state.started || Object.keys(state.answers).length > 0;

  const changeLanguage = () => {
    dispatch({ type: "set-language", language: language === "en" ? "ru" : "en" });
  };

  const reset = () => {
    dispatch({ type: "reset" });
    setConfirming(false);
    navigate("/intro");
  };

  return (
    <header className="site-header">
      <div className="site-header__bar">
        <a className="brand" href="#/intro">
          {copy.siteName}
        </a>
        <nav aria-label={language === "en" ? "Page controls" : "Управление страницей"}>
          <label className="theme-control">
            <span>{copy.themeLabel}</span>
            <select
              value={state.theme}
              onChange={(event) =>
                dispatch({ type: "set-theme", theme: event.target.value as ThemePreference })
              }
            >
              <option value="auto">{copy.themeAuto}</option>
              <option value="light">{copy.themeLight}</option>
              <option value="dark">{copy.themeDark}</option>
            </select>
          </label>
          <Button variant="quiet" onClick={changeLanguage} aria-label={copy.languageButton}>
            {copy.languageButton}
          </Button>
          {hasProgress && (
            <Button variant="danger" onClick={() => setConfirming(true)}>
              <RotateCcw aria-hidden="true" className="size-4" />
              {copy.startOver}
            </Button>
          )}
        </nav>
      </div>
      {confirming && (
        <div className="confirmation" role="alert">
          <p>{copy.startOverPrompt}</p>
          <div className="confirmation__actions">
            <Button variant="danger" onClick={reset}>
              {copy.confirmStartOver}
            </Button>
            <Button variant="secondary" onClick={() => setConfirming(false)}>
              {copy.cancel}
            </Button>
          </div>
        </div>
      )}
    </header>
  );
};

const IntroPage = ({ language, state }: SharedPageProps) => {
  const copy = uiCopy[language];
  const hero = imageCredits.find((image) => image.id === "oxbow")!;
  const resumeSection = state.lastSectionId ?? sections[0].id;
  const hasProgress = state.started && Object.keys(state.answers).length > 0;

  return (
    <main className="page page--intro" id="main-content">
      <div className="intro-grid page-enter">
        <div className="intro-copy">
          <h1>{copy.introTitle}</h1>
          <p className="owner-intro">{appCopy[language].ownerIntro}</p>
          <p className="lede">{copy.introBody}</p>
          <p className="medical-note">{appCopy[language].medicalNote}</p>
          <div className="version-history">
            <p>{copy.versionOne}</p>
            <p>{copy.versionTwo}</p>
          </div>
          <div className="primary-actions">
            {hasProgress && (
              <a
                className={buttonVariants({ variant: "primary" })}
                href={`#/assessment/${resumeSection}`}
              >
                {copy.resume}
                <ArrowRight aria-hidden="true" className="size-5" />
              </a>
            )}
            <a
              className={buttonVariants({ variant: hasProgress ? "secondary" : "primary" })}
              href="#/sources"
            >
              {copy.seeSources}
              <ArrowRight aria-hidden="true" className="size-5" />
            </a>
          </div>
        </div>
        <figure className="hero-art">
          <img src={hero.localPath} alt={hero.alt[language]} width="1464" height="1000" />
          <figcaption>
            {hero.title} · {hero.creator} · {hero.license}
          </figcaption>
        </figure>
      </div>
    </main>
  );
};

const SourcesPage = ({ language }: SharedPageProps) => {
  const copy = uiCopy[language];
  return (
    <main className="page page-enter" id="main-content">
      <div className="page-heading">
        <h1>{copy.sourcesTitle}</h1>
        <p className="lede">{copy.sourcesBody}</p>
        <p>{copy.sourceBalance}</p>
        <p>{copy.qualityNote}</p>
      </div>

      <Card className="language-card">
        <h2>{copy.languagesTitle}</h2>
        <ul className="language-list">
          {copy.representedLanguages.map((representedLanguage) => (
            <li key={representedLanguage}>{representedLanguage}</li>
          ))}
        </ul>
        <p className="language-note">{copy.translated}</p>
        <p className="language-note">{copy.processedLanguages}</p>
      </Card>

      <div className="source-list">
        {sources.map((source, index) => (
          <Card className="source-card" data-testid="source-card" key={source.id}>
            <p className="source-number">{String(index + 1).padStart(2, "0")}</p>
            <h2>{source.title}</h2>
            <p className="source-creator">{source.creator}</p>
            <dl>
              <div>
                <dt>{copy.sourceType}</dt>
                <dd>{source.sourceType[language]}</dd>
              </div>
              <div>
                <dt>{copy.originalLanguage}</dt>
                <dd>{source.originalLanguage[language]}</dd>
              </div>
              <div>
                <dt>{copy.captionBasis}</dt>
                <dd>{source.captionBasis[language]}</dd>
              </div>
            </dl>
            <a href={source.url} target="_blank" rel="noreferrer">
              {copy.openSource}
              <ExternalLink aria-hidden="true" className="size-4" />
            </a>
          </Card>
        ))}
      </div>

      <div className="sticky-action">
        <a className={buttonVariants({ variant: "primary" })} href={`#/assessment/${sections[0].id}`}>
          {copy.startAssessment}
          <ArrowRight aria-hidden="true" className="size-5" />
        </a>
      </div>
    </main>
  );
};

type QuestionCardProps = {
  question: Question;
  number: number;
  language: Language;
  answer: Answer | undefined;
  onAnswer: (value: Answer) => void;
};

const QuestionCard = ({ question, number, language, answer, onAnswer }: QuestionCardProps) => {
  const copy = uiCopy[language];
  const options: Array<{ value: Answer; label: string }> = copy.scale.map((label, index) => ({
    value: index as Answer,
    label,
  }));
  if (question.allowUnknown) options.push({ value: "unknown", label: copy.unknown });
  if (question.allowNotApplicable) {
    options.push({ value: "not-applicable", label: copy.notApplicable });
  }
  const labelId = `question-${question.id}`;

  return (
    <Card className="question-card" data-testid="question-card">
      <p className="question-number">{String(number).padStart(2, "0")}</p>
      <h2 id={labelId}>{question.text[language]}</h2>
      <RadioGroup
        aria-labelledby={labelId}
        value={answer === undefined ? "" : String(answer)}
        onValueChange={(value) => onAnswer(responseValue(value))}
      >
        {options.map((option) => (
          <RadioOption key={String(option.value)} value={String(option.value)} label={option.label} />
        ))}
      </RadioGroup>
    </Card>
  );
};

const AssessmentPage = ({ language, state, dispatch, sectionId }: SharedPageProps & { sectionId: string }) => {
  const copy = uiCopy[language];
  const sectionIndex = sections.findIndex((section) => section.id === sectionId);
  const section = sections[sectionIndex] ?? sections[0];
  const sectionQuestions = questions.filter((question) => question.sectionId === section.id);
  const image = imageCredits.find((item) => item.id === section.imageId)!;
  const complete = sectionQuestions.every((question) =>
    isCompleteAnswer(question, state.answers[question.id]),
  );
  const answeredCount = questions.filter((question) =>
    isCompleteAnswer(question, state.answers[question.id]),
  ).length;

  useEffect(() => {
    dispatch({ type: "visit-section", sectionId: section.id });
  }, [dispatch, section.id]);

  const goBack = () => {
    if (sectionIndex > 0) navigate(`/assessment/${sections[sectionIndex - 1].id}`);
    else navigate("/sources");
  };

  const goForward = () => {
    if (!complete) return;
    if (sectionIndex < sections.length - 1) {
      navigate(`/assessment/${sections[sectionIndex + 1].id}`);
    } else {
      navigate("/complete");
    }
  };

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (!event.altKey) return;
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        goBack();
      }
      if (event.key === "ArrowRight" && complete) {
        event.preventDefault();
        goForward();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    goForward();
  };

  const firstQuestionIndex = questions.findIndex((question) => question.id === sectionQuestions[0]?.id);

  return (
    <main className="page assessment-page page-enter" id="main-content">
      <div className="assessment-heading">
        <div>
          <p className="section-count">
            {copy.section} {sectionIndex + 1} / {sections.length}
          </p>
          <h1>{section.title[language]}</h1>
          <p className="lede">{section.introduction[language]}</p>
        </div>
        <figure className="section-art">
          <img src={image.localPath} alt={image.alt[language]} width="800" height="520" />
          <figcaption>
            <a href={image.sourceUrl} target="_blank" rel="noreferrer">
              {copy.imageCredit}: {image.title} · {image.creator} · {image.license}
            </a>
          </figcaption>
        </figure>
      </div>

      <div className="progress-block" aria-live="polite">
        <p>
          {answeredCount} / {questions.length} {copy.answered}
        </p>
        <progress value={answeredCount} max={questions.length}>
          {answeredCount} / {questions.length}
        </progress>
      </div>

      <p className="response-prompt">
        {section.id === "childhood" ? copy.childhoodPrompt : copy.responsePrompt}
      </p>

      <form onSubmit={submit}>
        <div className="question-list">
          {sectionQuestions.map((question, index) => (
            <QuestionCard
              key={question.id}
              question={question}
              number={firstQuestionIndex + index + 1}
              language={language}
              answer={state.answers[question.id]}
              onAnswer={(value) => dispatch({ type: "answer", questionId: question.id, value })}
            />
          ))}
        </div>
        <div className="assessment-actions">
          <Button variant="secondary" onClick={goBack}>
            <ArrowLeft aria-hidden="true" className="size-5" />
            {copy.back}
          </Button>
          <p className="shortcut">{copy.shortcut}</p>
          <Button type="submit" disabled={!complete}>
            {copy.continue}
            <ArrowRight aria-hidden="true" className="size-5" />
          </Button>
        </div>
      </form>
    </main>
  );
};

const CompletionPage = ({ language, state, dispatch }: SharedPageProps) => {
  const copy = uiCopy[language];
  const reveal = () => {
    dispatch({ type: "reveal" });
    navigate("/result");
  };
  return (
    <main className="page page--center page-enter" id="main-content">
      <Card className="completion-card">
        <h1>{copy.completeTitle}</h1>
        <p className="lede">{copy.completeBody}</p>
        <div className="primary-actions">
          <a
            className={buttonVariants({ variant: "secondary" })}
            href={`#/assessment/${sections[0].id}`}
          >
            {copy.reviewBeforeReveal}
          </a>
          <Button onClick={reveal} disabled={!canReveal(state.answers, questions)}>
            {copy.reveal}
          </Button>
        </div>
      </Card>
    </main>
  );
};

const ResultPage = ({ language, state, dispatch }: SharedPageProps) => {
  const copy = uiCopy[language];
  const [confirmingRetake, setConfirmingRetake] = useState(false);
  const result = scoreAssessment(state.answers, questions, sections);
  const sectionById = new Map(sections.map((section) => [section.id, section]));
  const domainById = new Map(result.domains.map((domain) => [domain.sectionId, domain]));
  const bandOrder = ["almost-none", "low", "moderate", "high", "very-high"] as const;
  const bandIndex = bandOrder.indexOf(result.band);
  const bandRanges = ["0–14", "15–34", "35–54", "55–74", "75–100"];
  const score = markerPercent(result.overall);
  const strongest = result.strongestSectionId
    ? sectionById.get(result.strongestSectionId)?.title[language]
    : null;
  const weakest = result.weakestSectionId
    ? sectionById.get(result.weakestSectionId)?.title[language]
    : null;
  const masking = domainById.get("masking");
  const childhood = domainById.get("childhood");
  const impact = domainById.get("context-impact");

  const retake = () => {
    dispatch({ type: "retake", firstSectionId: sections[0].id });
    navigate(`/assessment/${sections[0].id}`);
  };

  return (
    <main className="page result-page page-enter" data-testid="result" id="main-content">
      <section className="result-hero" aria-labelledby="result-title">
        <h1 id="result-title">{copy.scoreLabel}</h1>
        <p className="score" aria-label={`${copy.scoreLabel}: ${result.overall} ${copy.outOfHundred}`}>
          {result.overall}
          <span>/ 100</span>
        </p>
        <p className="band-name">{copy.bands[bandIndex]}</p>

        <div className="continuum" data-testid="continuum">
          <svg
            viewBox="0 0 100 18"
            role="img"
            aria-label={`${copy.continuumLabel}: ${result.overall} ${copy.outOfHundred}`}
          >
            <rect className="continuum__one" x="0" y="6" width="15" height="6" rx="2" />
            <rect className="continuum__two" x="15" y="6" width="20" height="6" />
            <rect className="continuum__three" x="35" y="6" width="20" height="6" />
            <rect className="continuum__four" x="55" y="6" width="20" height="6" />
            <rect className="continuum__five" x="75" y="6" width="25" height="6" rx="2" />
            <line className="continuum__marker-line" x1={score} y1="2" x2={score} y2="16" />
            <circle
              className="continuum__marker"
              data-testid="continuum-marker"
              cx={score}
              cy="3"
              r="2.5"
            />
          </svg>
          <ol className="continuum-labels" aria-label={copy.continuumLabel}>
            {copy.bands.map((band) => (
              <li key={band}>{band}</li>
            ))}
          </ol>
        </div>
        <p className="result-disclaimer">{appCopy[language].resultDisclaimer}</p>
      </section>

      <section className="result-summary" aria-labelledby="summary-heading">
        <h2 id="summary-heading">{copy.breakdownTitle}</h2>
        <div className="strength-copy">
          {strongest && (
            <p>
              {copy.strongest} <strong>{strongest}</strong>.
            </p>
          )}
          {weakest && (
            <p>
              {copy.weakest} <strong>{weakest}</strong>.
            </p>
          )}
        </div>
        <div className="domain-list">
          {result.domains.map((domain) => {
            const section = sectionById.get(domain.sectionId)!;
            return (
              <div className="domain-row" key={domain.sectionId}>
                <div>
                  <h3>{section.title[language]}</h3>
                  <output>{domain.score === null ? "—" : `${domain.score} / 100`}</output>
                </div>
                <progress value={domain.score ?? 0} max="100">
                  {domain.score ?? 0} / 100
                </progress>
              </div>
            );
          })}
        </div>
      </section>

      <section className="context-grid" aria-label={language === "en" ? "Result context" : "Контекст результата"}>
        <Card>
          <h2>{copy.maskingContext}</h2>
          <p>
            {copy.contextScore}: <strong>{masking?.score ?? "—"} / 100</strong>
          </p>
        </Card>
        <Card>
          <h2>{copy.childhoodContext}</h2>
          {childhood?.score === null ? (
            <p>{copy.noChildhood}</p>
          ) : (
            <p>
              {copy.contextScore}: <strong>{childhood?.score ?? "—"} / 100</strong>
            </p>
          )}
        </Card>
        <Card>
          <h2>{copy.impactContext}</h2>
          <p>
            {copy.contextScore}: <strong>{impact?.score ?? "—"} / 100</strong>
          </p>
        </Card>
      </section>

      <div className="result-actions">
        <Button variant="secondary" onClick={() => navigate(`/assessment/${sections[0].id}`)}>
          {copy.reviewAnswers}
        </Button>
        <Button onClick={() => setConfirmingRetake(true)}>{copy.retake}</Button>
      </div>
      {confirmingRetake && (
        <div className="confirmation confirmation--result" role="alert">
          <p>{copy.retakePrompt}</p>
          <div className="confirmation__actions">
            <Button variant="danger" onClick={retake}>
              {copy.confirmRetake}
            </Button>
            <Button variant="secondary" onClick={() => setConfirmingRetake(false)}>
              {copy.cancel}
            </Button>
          </div>
        </div>
      )}

      <details className="methodology">
        <summary>{copy.methodology}</summary>
        <div className="methodology__content">
          <p>{copy.methodSummary}</p>
          <section>
            <h2>{copy.weightingTitle}</h2>
            <p>{copy.weightingBody}</p>
            <ul>
              {sections.map((section) => (
                <li key={section.id}>
                  {section.title[language]}: {Math.round(DOMAIN_WEIGHTS[section.id] * 100)}%
                </li>
              ))}
            </ul>
          </section>
          <section>
            <h2>{copy.bandsTitle}</h2>
            <p>{copy.bandsBody}</p>
            <ul>
              {copy.bands.map((band, index) => (
                <li key={band}>
                  {band}: {bandRanges[index]}
                </li>
              ))}
            </ul>
          </section>
          <section>
            <h2>{copy.provenanceTitle}</h2>
            <ol className="provenance-list">
              {questions.map((question) => (
                <li key={question.id}>
                  <p>{question.text[language]}</p>
                  <span>{copy.sourcesForQuestion}: </span>
                  {question.sourceIds.map((sourceId, index) => {
                    const source = sources.find((item) => item.id === sourceId)!;
                    return (
                      <span key={sourceId}>
                        {index > 0 && ", "}
                        <a href={source.url} target="_blank" rel="noreferrer">
                          {Number(sourceId.slice(1))}
                        </a>
                      </span>
                    );
                  })}
                </li>
              ))}
            </ol>
          </section>
          <section>
            <h2>{copy.guidanceTitle}</h2>
            <ul>
              {officialGuidance.map((item) => (
                <li key={item.url}>
                  <a href={item.url} target="_blank" rel="noreferrer">
                    {item.name}
                  </a>
                </li>
              ))}
            </ul>
          </section>
          <section>
            <h2>{copy.instrumentsTitle}</h2>
            <p>{copy.instrumentsBody}</p>
            <ul>
              {instrumentReviews.map((item) => (
                <li key={item.url}>
                  <a href={item.url} target="_blank" rel="noreferrer">
                    {item.name}
                  </a>
                  : {item.reuseDecision[language]}
                </li>
              ))}
            </ul>
          </section>
          <section>
            <h2>{copy.imageCreditsTitle}</h2>
            <ul>
              {imageCredits.map((image) => (
                <li key={image.id}>
                  <a href={image.sourceUrl} target="_blank" rel="noreferrer">
                    {image.title}
                  </a>
                  , {image.creator} · {image.license}
                </li>
              ))}
            </ul>
          </section>
        </div>
      </details>
    </main>
  );
};

export const App = () => {
  const [state, dispatch] = useReducer(
    reduceAssessmentState,
    undefined,
    () => restoreState(window.localStorage.getItem(STORAGE_KEY)),
  );
  const [route, setRoute] = useState<Route>(() => parseRoute());
  const [systemPrefersDark, setSystemPrefersDark] = useState(() =>
    window.matchMedia("(prefers-color-scheme: dark)").matches,
  );
  const mainRef = useRef<HTMLDivElement>(null);
  const ready = useMemo(() => canReveal(state.answers, questions), [state.answers]);
  const resolvedTheme = resolveTheme(state.theme, systemPrefersDark);

  useEffect(() => {
    if (!window.location.hash) navigate("/intro", true);
    const updateRoute = () => setRoute(parseRoute());
    window.addEventListener("hashchange", updateRoute);
    return () => window.removeEventListener("hashchange", updateRoute);
  }, []);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, serializeState(state));
    document.documentElement.lang = state.language;
    document.title = uiCopy[state.language].siteName;
  }, [state]);

  useEffect(() => {
    const query = window.matchMedia("(prefers-color-scheme: dark)");
    const updateSystemTheme = (event: MediaQueryListEvent) => setSystemPrefersDark(event.matches);
    query.addEventListener("change", updateSystemTheme);
    return () => query.removeEventListener("change", updateSystemTheme);
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = resolvedTheme;
    document.documentElement.style.colorScheme = resolvedTheme;
  }, [resolvedTheme]);

  useEffect(() => {
    mainRef.current?.focus();
  }, [route]);

  useEffect(() => {
    if (route.page === "assessment" && !sections.some((section) => section.id === route.sectionId)) {
      navigate(`/assessment/${sections[0].id}`, true);
    }
    if (route.page === "complete" && !ready) {
      navigate(`/assessment/${firstIncompleteSection(state.answers) ?? sections[0].id}`, true);
    }
    if (route.page === "result" && (!ready || !state.revealed)) {
      navigate(ready ? "/complete" : `/assessment/${firstIncompleteSection(state.answers) ?? sections[0].id}`, true);
    }
  }, [ready, route, state.answers, state.revealed]);

  const shared = { language: state.language, state, dispatch };
  let page;
  if (route.page === "sources") page = <SourcesPage {...shared} />;
  else if (route.page === "assessment") {
    page = <AssessmentPage {...shared} sectionId={route.sectionId} />;
  } else if (route.page === "complete" && ready) page = <CompletionPage {...shared} />;
  else if (route.page === "result" && ready && state.revealed) page = <ResultPage {...shared} />;
  else page = <IntroPage {...shared} />;

  return (
    <div className="app-shell" ref={mainRef} tabIndex={-1}>
      <a className="skip-link" href="#main-content">
        {state.language === "en" ? "Skip to main content" : "Перейти к основному содержанию"}
      </a>
      <Header {...shared} />
      {page}
    </div>
  );
};
