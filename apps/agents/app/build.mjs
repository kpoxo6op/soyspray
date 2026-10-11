import { cp, mkdir, rm, readFile } from "node:fs/promises";
const source = new URL("./src/", import.meta.url);
const destination = new URL("./dist/", import.meta.url);
await rm(destination, { recursive: true, force: true });
await mkdir(destination, { recursive: true });
await cp(source, destination, { recursive: true });
const content = JSON.parse(
    await readFile(new URL("content.json", destination), "utf8"),
);
if (content.lessons?.length < 6 || !content.talkChapters?.length)
    throw Error("Approved teaching content is incomplete");
for (const chapter of content.talkChapters) {
    if (!(chapter.end > chapter.start)) throw Error("Invalid chapter interval");
}
console.log("Built static workshop with approved content");
