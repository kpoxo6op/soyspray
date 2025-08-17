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

## Post-Processing (Snatched → Open Button)

After a book shows as "Snatched", it needs to be processed to show the "Open" button.

### Automatic Post-Processing
**Enable in LazyLibrarian Settings → Processing:**
- **Post-Processing Interval**: `10` minutes
- **Move Files**: `False` (keeps qBittorrent files for seeding)

### Manual Post-Processing Options

**Option 1: Force Post-Processing (for folder downloads like 1984)**
```bash
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=forceProcess&apikey=3723d36aa1e9e9955e3bf8982e94ee3c"
```

**Option 2: Import Alternative (for single file downloads like Harry Potter)**
```bash
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=importAlternate&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&dir=/downloads/books"
```

**GUI Alternative:**
1. Go to **LazyLibrarian → Manage → Import Books**
2. Set import directory: `/downloads/books`
3. Run import scan

### Download Types
- **Folder downloads** (like 1984): Use `forceProcess`
- **Single file downloads** (like Harry Potter): Use `importAlternate`
- **Both types**: Automatic processing works with 10-minute intervals

## Integration Status

✅ **Tested and Working** - Complete API flow: findBook → addBook → queueBook → searchBook → download → post-processing → "Open" button available

## Homework - Public Domain Books to Try

### Popular Books (More Likely to Have Downloads)

**The Hobbit by J.R.R. Tolkien**
```bash
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=findBook&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&name=The+Hobbit+J+R+R+Tolkien" | jq '.[0:3]'
```

**1984 by George Orwell**
```bash
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=findBook&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&name=1984+George+Orwell" | jq '.[0:3]'
```

**Animal Farm by George Orwell**
```bash
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=findBook&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&name=Animal+Farm+George+Orwell" | jq '.[0:3]'
```

**Brave New World by Aldous Huxley**
```bash
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=findBook&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&name=Brave+New+World+Aldous+Huxley" | jq '.[0:3]'
```

**To Kill a Mockingbird by Harper Lee**
```bash
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=findBook&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&name=To+Kill+a+Mockingbird+Harper+Lee" | jq '.[0:3]'
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
