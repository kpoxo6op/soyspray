// The Parts button opens the print and buy sheet in a dialog; opening it pauses playback.
export function createPartsUI({ player, sheet }) {
  const dialog = document.getElementById('partsSheet');
  dialog.innerHTML = sheet();
  const button = document.getElementById('btnParts');
  const close = document.getElementById('closeParts');
  button.addEventListener('click', () => {
    player.pause();
    dialog.showModal();
    close.focus();
  });
  close.addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', (e) => {
    if (e.target === dialog) dialog.close();
  });
  dialog.addEventListener('close', () => button.focus());
}
