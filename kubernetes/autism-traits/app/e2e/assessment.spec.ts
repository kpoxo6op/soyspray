import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const answerSection = async (page: Page, label = "Often") => {
  const cards = page.getByTestId("question-card");
  const count = await cards.count();
  expect(count).toBeGreaterThan(0);
  for (let index = 0; index < count; index += 1) {
    await cards.nth(index).getByRole("radio", { name: label, exact: true }).click();
  }
};

const startAssessment = async (page: Page) => {
  await page.goto("/");
  await page.getByRole("link", { name: "See the sources" }).click();
  await expect(page.getByTestId("source-card")).toHaveCount(30);
  await page.getByRole("link", { name: "Start the assessment" }).click();
  await expect(page).toHaveURL(/#\/assessment\/conversation$/);
};

const completeAssessment = async (page: Page) => {
  let visitedSections = 0;
  while (!/#\/complete$/.test(page.url())) {
    expect(visitedSections).toBeLessThan(100);
    await expect(page.getByTestId("result")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Continue" })).toBeDisabled();
    await answerSection(page);
    await expect(page.getByRole("button", { name: "Continue" })).toBeEnabled();
    await page.getByRole("button", { name: "Continue" }).click();
    visitedSections += 1;
  }
  await expect(page).toHaveURL(/#\/complete$/);
};

const continueThroughAnsweredSections = async (page: Page) => {
  let visitedSections = 0;
  while (!/#\/complete$/.test(page.url())) {
    expect(visitedSections).toBeLessThan(100);
    await page.getByRole("button", { name: "Continue" }).click();
    visitedSections += 1;
  }
};

test("intro and source pages preserve the required content without retaining preferences", async ({ page }) => {
  const initialDocument = await page.request.get("/");
  expect(initialDocument.ok()).toBe(true);
  expect(await initialDocument.text()).toContain("<title>Detailed autism questionnaire</title>");

  await page.goto("/");
  await expect(
    page.getByText("I am already diagnosed with mild ASD and am taking this test for a video."),
  ).toBeVisible();
  await expect(
    page.getByText(
      "This is not a diagnostic test. If it makes you curious, seek a professional assessment like I did.",
    ),
  ).toBeVisible();
  await expect(
    page.getByText(
      "Your answers and score stay only in this browser tab. They are not transmitted or retained and disappear when you refresh or close the page. Cloudflare may process connection metadata to deliver the site.",
    ),
  ).toBeVisible();
  await expect(page.getByRole("radio", { name: "Full", exact: true })).toBeChecked();
  await expect(page.getByRole("link", { name: "See the sources" })).toBeVisible();
  await page.getByRole("radio", { name: "Short", exact: true }).click();
  await expect(page.getByRole("radio", { name: "Short", exact: true })).toBeChecked();
  await page.getByRole("radio", { name: "Full", exact: true }).click();
  await expect(page.getByRole("button", { name: "Start full" })).toBeVisible();

  const selectorBox = await page.getByRole("radiogroup", { name: "Choose a length" }).boundingBox();
  const startBox = await page.getByRole("button", { name: "Start full" }).boundingBox();
  const versionLinkBox = await page.getByRole("link", { name: "Version info" }).boundingBox();
  expect(startBox?.width).toBe(selectorBox?.width);
  expect(versionLinkBox!.y).toBeGreaterThan(startBox!.y + startBox!.height);

  const fullOption = page.getByRole("radio", { name: "Full", exact: true });
  await expect(fullOption).toHaveCSS("background-color", "rgb(21, 91, 69)");
  await expect(fullOption).toHaveCSS("color", "rgb(246, 246, 243)");
  expect(await fullOption.evaluate((element) => getComputedStyle(element).transitionDuration)).not.toBe(
    "0s",
  );

  const shortOption = page.getByRole("radio", { name: "Short", exact: true });
  await shortOption.click();
  await expect(shortOption).toBeChecked();
  await expect(shortOption).toHaveCSS("background-color", "rgb(21, 91, 69)");
  await expect(fullOption).not.toHaveCSS("background-color", "rgb(21, 91, 69)");
  await fullOption.click();

  await page.getByRole("combobox", { name: "Theme" }).selectOption("dark");
  await shortOption.click();
  await expect(shortOption).toHaveCSS("background-color", "rgb(145, 216, 188)");
  await expect(shortOption).toHaveCSS("color", "rgb(23, 26, 24)");
  await page.getByRole("combobox", { name: "Theme" }).selectOption("auto");
  await fullOption.click();

  await page.getByRole("link", { name: "Version info" }).click();
  await expect(page).toHaveURL(/#\/versions$/);
  await expect(page.getByRole("heading", { name: "Version 2.1.0" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Short · 50 questions" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Full · 328 questions" })).toBeVisible();
  await expect(
    page.getByText("v1 - mediocrity AI created because I did not ask to adhere to my vision."),
  ).toBeVisible();
  await expect(
    page.getByText("v2 - 328 detailed questions drawn from 30 captioned videos. Minimal AI rewriting. Simpler design."),
  ).toBeVisible();

  await page.getByRole("button", { name: "Русский" }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "ru");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page).toHaveTitle("Detailed autism questionnaire");
  await page.getByRole("button", { name: "Русский" }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "ru");
  await expect(page).toHaveTitle("Подробный опрос об аутизме");
  await expect(page.getByRole("heading", { name: "Версия 2.1.0" })).toBeVisible();
  await expect(
    page.getByText(
      "v2 — 328 подробных вопросов по 30 видео с субтитрами. Минимум ИИ-редактирования. Более простой дизайн.",
    ),
  ).toBeVisible();
  await expect(
    page.getByText(
      "v1 — посредственный результат ИИ, потому что я не попросил ИИ следовать моему замыслу.",
    ),
  ).toBeVisible();
  await page.getByRole("link", { name: "Назад к опросу" }).click();
  await expect(page.getByRole("radio", { name: "Полный", exact: true })).toBeChecked();
  await expect(page.getByRole("button", { name: "English" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Спокойный способ заметить закономерности" })).toBeVisible();
  await page.getByRole("link", { name: "Посмотреть источники" }).click();
  await expect(page.getByTestId("source-card")).toHaveCount(30);
  await expect(page.locator(".language-list").getByText("Бразильский португальский")).toBeVisible();
  await expect(page.getByText("Содержание опроса доступно на английском и русском")).toBeVisible();

  await page.getByRole("button", { name: "English" }).click();
  await expect(page).toHaveTitle("Detailed autism questionnaire");
  await expect(page.getByTestId("source-card")).toHaveCount(30);
  const representedLanguages = page.locator(".language-list");
  await expect(representedLanguages.getByText("Brazilian Portuguese", { exact: true })).toBeVisible();
  await expect(representedLanguages.getByText("Korean", { exact: true })).toBeVisible();
  await expect(page.getByText("Processed assessment content: English and Russian")).toBeVisible();
  await expect(page.getByTestId("source-card").first().getByRole("link")).toHaveAttribute(
    "href",
    /^https:\/\/www\.youtube\.com\/watch\?v=/,
  );
});

test("short and full run as separate question sets", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop");
  await page.goto("/");

  await page.getByRole("radio", { name: "Short", exact: true }).click();
  await page.getByRole("button", { name: "Start short" }).click();
  await expect(page).toHaveURL(/#\/assessment\/conversation$/);
  await expect(page.getByText("0 / 50 answered")).toBeVisible();
  await expect(page.getByTestId("question-card")).toHaveCount(4);
  await page
    .getByTestId("question-card")
    .first()
    .getByRole("radio", { name: "Often", exact: true })
    .click();
  await completeAssessment(page);
  await page.getByRole("button", { name: "Reveal my result" }).click();
  await expect(page.getByTestId("result")).toBeVisible();

  await page.getByRole("link", { name: "Detailed autism questionnaire" }).click();
  await page.getByRole("radio", { name: "Full", exact: true }).click();
  await page.getByRole("button", { name: "Start full" }).click();
  await expect(page.getByText("0 / 328 answered")).toBeVisible();
  await expect(page.getByTestId("question-card").first().getByRole("radio", { checked: true })).toHaveCount(
    0,
  );
});

test("mouse flow keeps the result hidden until explicit reveal and supports editing and retake", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "desktop");
  test.slow();
  await startAssessment(page);
  await completeAssessment(page);

  await expect(page.getByTestId("result")).toHaveCount(0);
  await expect(page.getByText("Ready to reveal")).toBeVisible();
  await expect(page.locator(".completion-card")).toHaveCSS("background-color", "rgba(0, 0, 0, 0)");
  await expect(page.locator(".completion-card")).toHaveCSS("border-radius", "0px");
  await page.getByRole("button", { name: "Reveal my result" }).click();
  await expect(page.getByTestId("result")).toBeVisible();
  for (const surface of [
    ".result-hero",
    ".strength-copy p",
    ".domain-row",
    ".context-grid > section",
  ]) {
    await expect(page.locator(surface).first()).toHaveCSS("background-color", "rgba(0, 0, 0, 0)");
    await expect(page.locator(surface).first()).toHaveCSS("border-radius", "0px");
  }

  const track = await page.getByTestId("continuum").boundingBox();
  const marker = await page.getByTestId("continuum-marker").boundingBox();
  expect(track).not.toBeNull();
  expect(marker).not.toBeNull();
  expect(marker!.x).toBeGreaterThanOrEqual(track!.x - marker!.width / 2);
  expect(marker!.x + marker!.width).toBeLessThanOrEqual(track!.x + track!.width + marker!.width / 2);

  await page.getByRole("button", { name: "Review answers" }).click();
  await expect(page).toHaveURL(/#\/assessment\/conversation$/);
  const first = page.getByTestId("question-card").first();
  await first.getByRole("radio", { name: "Sometimes", exact: true }).click();
  await expect(page.getByTestId("result")).toHaveCount(0);
  await continueThroughAnsweredSections(page);
  await expect(page.getByTestId("result")).toHaveCount(0);
  await page.getByRole("button", { name: "Reveal my result" }).click();

  await page.getByRole("button", { name: "Retake assessment" }).click();
  await page.getByRole("button", { name: "Confirm retake" }).click();
  await expect(page).toHaveURL(/#\/assessment\/conversation$/);
  await expect(page.getByTestId("question-card").first().getByRole("radio", { checked: true })).toHaveCount(
    0,
  );
});

test("browser Back keeps answers in memory and refresh clears them", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop");
  await startAssessment(page);

  const cards = page.getByTestId("question-card");
  for (let index = 0; index < (await cards.count()); index += 1) {
    const firstOption = cards.nth(index).getByRole("radio").first();
    await firstOption.focus();
    await page.keyboard.press("Space");
    await expect(firstOption).toBeChecked();
  }
  await page.keyboard.press("Alt+ArrowRight");
  await expect(page).toHaveURL(/#\/assessment\/relationships$/);
  await page.goBack();
  await expect(page).toHaveURL(/#\/assessment\/conversation$/);
  await expect(cards.first().getByRole("radio", { checked: true })).toHaveCount(1);

  await page.reload();
  await expect(cards.first().getByRole("radio", { checked: true })).toHaveCount(0);
  await page.goto("/#/intro");
  await expect(page.getByRole("link", { name: "Resume assessment" })).toHaveCount(0);
});

test("changing sections scrolls to the top", async ({ page }) => {
  await startAssessment(page);
  await answerSection(page);
  await page.getByRole("button", { name: "Continue" }).scrollIntoViewIfNeeded();
  expect(await page.evaluate(() => window.scrollY)).toBeGreaterThan(0);

  await page.getByRole("button", { name: "Continue" }).click();

  await expect(page).toHaveURL(/#\/assessment\/relationships$/);
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);
});

test("start over clears in-memory answers without changing language or theme", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop");
  await startAssessment(page);
  await page
    .getByTestId("question-card")
    .first()
    .getByRole("radio", { name: "Sometimes", exact: true })
    .click();
  await page.getByRole("combobox", { name: "Theme" }).selectOption("dark");
  await page.getByRole("button", { name: "Русский" }).click();
  await page.getByRole("button", { name: "Начать заново" }).click();
  await page.getByRole("button", { name: "Подтвердить начало заново" }).click();
  await expect(page).toHaveURL(/#\/intro$/);
  await expect(page.locator("html")).toHaveAttribute("lang", "ru");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.getByRole("combobox", { name: "Тема" })).toHaveValue("dark");
  await expect(page.getByRole("link", { name: "Продолжить опрос" })).toHaveCount(0);
});

test("Auto theme follows system changes and stays selected after reload", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop");
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/");

  const theme = page.getByRole("combobox", { name: "Theme" });
  await expect(theme).toHaveValue("auto");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");

  await page.emulateMedia({ colorScheme: "light" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.reload();
  await expect(theme).toHaveValue("auto");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});

test("explicit Light and Dark themes override the system only until refresh", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop");
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/");

  const theme = page.getByRole("combobox", { name: "Theme" });
  await theme.selectOption("light");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.emulateMedia({ colorScheme: "light" });
  await page.emulateMedia({ colorScheme: "dark" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.reload();
  await expect(theme).toHaveValue("auto");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");

  await page.emulateMedia({ colorScheme: "light" });
  await theme.selectOption("dark");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.reload();
  await expect(theme).toHaveValue("auto");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});

test("legacy assessment storage is deleted and never restored", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop");
  await page.goto("/");
  await page.evaluate(() => {
    window.localStorage.setItem(
      "autism-traits-assessment:v1",
      JSON.stringify({ language: "ru", answers: { q01: 4 }, started: true }),
    );
  });
  await page.reload();

  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.getByRole("link", { name: "Resume assessment" })).toHaveCount(0);
  expect(
    await page.evaluate(() => window.localStorage.getItem("autism-traits-assessment:v1")),
  ).toBeNull();
});

test("content stays flat while mobile answers retain bordered touch controls", async ({
  page,
}, testInfo) => {
  await page.goto("/#/sources");
  for (const surface of [page.locator(".language-card"), page.getByTestId("source-card").first()]) {
    const style = await surface.evaluate((element) => {
      const computed = getComputedStyle(element);
      return {
        backgroundColor: computed.backgroundColor,
        borderRadius: computed.borderRadius,
      };
    });
    expect(style.backgroundColor).toBe("rgba(0, 0, 0, 0)");
    expect(style.borderRadius).toBe("0px");
  }

  await page.goto("/#/assessment/conversation");
  const card = page.getByTestId("question-card").first();
  const option = card.getByRole("radio", { name: "Often", exact: true });
  const cardStyle = await card.evaluate((element) => {
    const computed = getComputedStyle(element);
    return {
      backgroundColor: computed.backgroundColor,
      borderRadius: computed.borderRadius,
    };
  });
  expect(cardStyle.backgroundColor).toBe("rgba(0, 0, 0, 0)");
  expect(cardStyle.borderRadius).toBe("0px");

  const optionStyle = async () =>
    option.evaluate((element) => {
      const computed = getComputedStyle(element);
      return {
        backgroundColor: computed.backgroundColor,
        borderRadius: computed.borderRadius,
        borderTopWidth: computed.borderTopWidth,
      };
    });

  const resting = await optionStyle();
  if (testInfo.project.name === "mobile") {
    expect(Number.parseFloat(resting.borderRadius)).toBeGreaterThan(0);
    expect(Number.parseFloat(resting.borderTopWidth)).toBeGreaterThan(0);
  } else {
    expect(resting.backgroundColor).toBe("rgba(0, 0, 0, 0)");
    expect(resting.borderRadius).toBe("0px");
    expect(resting.borderTopWidth).toBe("0px");
    await page.getByRole("combobox", { name: "Theme" }).selectOption("dark");
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await expect(option).toHaveCSS("background-color", "rgba(0, 0, 0, 0)");
    await option.hover();
    await expect.poll(async () => (await optionStyle()).backgroundColor).not.toBe(resting.backgroundColor);
  }

  await option.click();
  await expect(option).toBeChecked();
  await expect.poll(async () => (await optionStyle()).backgroundColor).not.toBe(resting.backgroundColor);
});

test("phone-sized touch targets and responsive pages avoid horizontal overflow", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "mobile");
  await startAssessment(page);
  const option = page
    .getByTestId("question-card")
    .first()
    .getByRole("radio", { name: "Often", exact: true });
  const box = await option.boundingBox();
  expect(box).not.toBeNull();
  expect(box!.height).toBeGreaterThanOrEqual(44);
  expect(box!.width).toBeGreaterThanOrEqual(44);
  await option.tap();
  await expect(option).toBeChecked();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBe(true);
});

test("key pages have no detectable WCAG A or AA violations", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop");
  test.slow();
  await page.goto("/");
  expect((await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze()).violations).toEqual([]);

  await startAssessment(page);
  expect((await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze()).violations).toEqual([]);

  await completeAssessment(page);
  expect((await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze()).violations).toEqual([]);

  await page.getByRole("button", { name: "Reveal my result" }).click();
  expect((await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze()).violations).toEqual([]);
});

test("reduced-motion preference removes meaningful animation", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  expect(await page.evaluate(() => matchMedia("(prefers-reduced-motion: reduce)").matches)).toBe(true);
  const longestMotion = await page.evaluate(() => {
    const seconds = (value: string) =>
      Math.max(...value.split(",").map((part) => Number.parseFloat(part) || 0));
    return Math.max(
      ...Array.from(document.querySelectorAll("*")).map((element) => {
        const style = getComputedStyle(element);
        return Math.max(seconds(style.animationDuration), seconds(style.transitionDuration));
      }),
    );
  });
  expect(longestMotion).toBeLessThanOrEqual(0.01);
});

test("desktop and 16:9 layouts keep the primary content inside the viewport", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "desktop");
  for (const viewport of [
    { width: 1280, height: 900 },
    { width: 1440, height: 810 },
  ]) {
    await page.setViewportSize(viewport);
    await page.goto("/");
    const main = await page.locator("main").boundingBox();
    expect(main).not.toBeNull();
    expect(main!.x).toBeGreaterThanOrEqual(0);
    expect(main!.x + main!.width).toBeLessThanOrEqual(viewport.width);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
      viewport.width,
    );
  }
});
