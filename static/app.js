document.addEventListener('DOMContentLoaded', () => {
  const startBtn = document.getElementById('btn-start');
  const joinBtn = document.getElementById('btn-join');
  const modalStart = document.getElementById('modal-start');
  const modalJoin = document.getElementById('modal-join');
  
  if (startBtn && modalStart) {
    startBtn.addEventListener('click', () => {
      modalStart.classList.add('active');
    });
  }
  
  if (joinBtn && modalJoin) {
    joinBtn.addEventListener('click', () => {
      modalJoin.classList.add('active');
    });
  }
  
  document.querySelectorAll('.close-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.target.closest('.modal-overlay').classList.remove('active');
    });
  });
  
  // Close modal on click outside
  document.querySelectorAll('.modal-overlay').forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.classList.remove('active');
      }
    });
  });
});
