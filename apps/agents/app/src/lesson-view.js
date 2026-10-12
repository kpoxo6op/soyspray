import { editorialLessons } from "./lesson-content.js";

export function renderLessonBody(lesson) {
    return editorialLessons[lesson.id].bodyHtml.join("\n");
}
