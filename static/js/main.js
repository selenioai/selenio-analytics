function toggleTheme(){
  var html=document.documentElement;
  var next=html.getAttribute('data-theme')==='dark'?'light':'dark';
  html.setAttribute('data-theme',next);
  localStorage.setItem('selenio-theme',next);
}
(function(){
  var saved=localStorage.getItem('selenio-theme');
  if(saved)document.documentElement.setAttribute('data-theme',saved);
})();
document.addEventListener('DOMContentLoaded',function(){
  document.querySelectorAll('.flash').forEach(function(el){
    setTimeout(function(){el.style.opacity='0';el.style.transition='opacity .5s'},4000);
    setTimeout(function(){el.remove()},4500);
  });
});
