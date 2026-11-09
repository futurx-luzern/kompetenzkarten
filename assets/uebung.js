// Kleine Zuordnungs-Übung: Antwort antippen, sofort Rückmeldung.
document.querySelectorAll('.uebung').forEach(function (liste) {
  var stand = liste.parentElement.querySelector('.uebung-stand');
  var total = liste.querySelectorAll('li').length;
  function zaehle() {
    var ok = liste.querySelectorAll('li.geloest').length;
    if (stand) stand.textContent = ok + ' von ' + total + ' richtig zugeordnet' + (ok === total ? '. Super, du hast das Prinzip verstanden!' : '');
  }
  liste.querySelectorAll('li').forEach(function (eintrag) {
    var richtig = eintrag.getAttribute('data-richtig');
    var info = eintrag.querySelector('.rueckmeldung');
    eintrag.querySelectorAll('.wahl button').forEach(function (knopf) {
      knopf.addEventListener('click', function () {
        if (eintrag.classList.contains('geloest')) return;
        if (knopf.textContent === richtig) {
          knopf.classList.add('richtig');
          eintrag.classList.add('geloest');
          info.textContent = '✓ ' + eintrag.getAttribute('data-erklaerung');
        } else {
          knopf.classList.add('falsch');
          info.textContent = 'Noch nicht. Überleg nochmals: Ist es wichtig? Ist es dringend?';
          if (eintrag.getAttribute('data-hinweis')) info.textContent = 'Noch nicht. ' + eintrag.getAttribute('data-hinweis');
        }
        zaehle();
      });
    });
  });
  zaehle();
});
