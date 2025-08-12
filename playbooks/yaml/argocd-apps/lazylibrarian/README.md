# LazyLibrarian API Commands

## Complete Book Download Workflow

### 1. Find Book

```bash
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=findBook&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&name=Alice+in+Wonderland+Lewis+Carroll" | jq '.[0:3]'
```

### 2. Add Book to Database

```bash
# Use bookid from findBook response
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=addBook&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&id=28190157"
```

### 3. Queue Book for Download

```bash
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=queueBook&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&id=28190157&type=eBook"
```

### 4. Trigger Search and Download

```bash
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=searchBook&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&id=28190157&wait=true"
```

### 5. Check Download Status

```bash
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=getSnatched&apikey=3723d36aa1e9e9955e3bf8982e94ee3c" | jq
```

## Integration Status

✅ **Tested and Working** - Complete API flow: findBook → addBook → queueBook → searchBook → download → "Open" button available

## Homework - Public Domain Books to Try

### Classic Literature (All Public Domain)

**Pride and Prejudice by Jane Austen**
```bash
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=findBook&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&name=Pride+and+Prejudice+Jane+Austen" | jq '.[0:3]'
```

**The Adventures of Sherlock Holmes by Arthur Conan Doyle**
```bash
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=findBook&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&name=Adventures+of+Sherlock+Holmes+Arthur+Conan+Doyle" | jq '.[0:3]'
```

**Frankenstein by Mary Shelley**
```bash
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=findBook&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&name=Frankenstein+Mary+Shelley" | jq '.[0:3]'
```

**The Great Gatsby by F. Scott Fitzgerald**
```bash
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=findBook&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&name=Great+Gatsby+F+Scott+Fitzgerald" | jq '.[0:3]'
```

**Dracula by Bram Stoker**
```bash
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=findBook&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&name=Dracula+Bram+Stoker" | jq '.[0:3]'
```

**The Time Machine by H.G. Wells**
```bash
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=findBook&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&name=Time+Machine+H+G+Wells" | jq '.[0:3]'
```

### Instructions

1. **Run any findBook command above** to see available editions
2. **Pick the best match** (look for highest rating, proper author, good description)
3. **Copy the bookid** from the JSON response
4. **Follow the 4-step workflow**:
   ```bash
   # Replace BOOK_ID with the actual ID from step 1
   curl -s "https://lazylibrarian.soyspray.vip/api?cmd=addBook&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&id=BOOK_ID"
   curl -s "https://lazylibrarian.soyspray.vip/api?cmd=queueBook&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&id=BOOK_ID&type=eBook"
   curl -s "https://lazylibrarian.soyspray.vip/api?cmd=searchBook&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&id=BOOK_ID&wait=true"
   curl -s "https://lazylibrarian.soyspray.vip/api?cmd=getSnatched&apikey=3723d36aa1e9e9955e3bf8982e94ee3c" | jq
   ```
5. **Wait a few minutes** for processing
6. **Check the web UI** - book should show "Open" button when ready
