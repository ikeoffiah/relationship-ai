let V = {};
let ven = false;
let vuser = false;
let vtest = '';
let vpath = '';
let vpage = '';
let vlux = 0;
V['_navlang'] = window.navigator.language.slice(0, 2);
V['_navru'] = V['_navlang'] == 'ru' || V['_navlang'] == 'RU' ? true : false;

function getVar (cname) {
  let cid = vtest + '-' + cname;
  let r = sessionStorage.getItem(cid);
  if (r == undefined || r == null) { return ""; }
  return r; }

function setVar (cname, cvalue) {
  let cid = vtest + '-' + cname;
  return sessionStorage.setItem(cid, cvalue); }

function delVar (cname) {
  let cid = vtest + '-' + cname;
  sessionStorage.removeItem(cid); }

function setSVar (cname, cvalue) {
  return sessionStorage.setItem(cname, cvalue); }

function getSVar (cname) {
  let r = sessionStorage.getItem(cname);
  if (r == undefined || r == null) { return ""; }
  return r; }

function setLocal (cname, cvalue) {
  return localStorage.setItem(cname, cvalue); }

function getLocal (cname) {
  let r = localStorage.getItem(cname);
  if (r == undefined || r == null) { return ""; }
  return r; }

function delLocal (cname) {
  localStorage.removeItem(cname); }

function getRandomInt (xmin, xmax) {
  return Math.floor(Math.random() * (xmax - xmin + 1)) + xmin; }

function int (n) {
  if (n == undefined || n == null || n == "") { return 0; }
  return parseInt(n); }

function str (s) {
  if (s == undefined || s == null) { return ""; }
  return s.toString(); }

function timeStart () {
  V['_start'] = Math.floor(new Date().getTime() / 1000);
  setVar('start', V['_start']) }

function timeElapsed (time) { 
  var minutes = Math.floor(time/60); 
  var seconds = time%60; 
  var hours = Math.floor(minutes/60); 
  minutes = minutes%60; 
  if (seconds < 10) { seconds = "0" + seconds; } 
  if (minutes < 10 && hours > 0) { minutes = "0" + minutes; } 
  var elapsed = "" + minutes + ':' + seconds; 
  if (hours > 0) { elapsed = "" + hours + ':' + elapsed; } 
  return elapsed; } 

function storageCheck ()
{
  let storage = 0;
  try {
    let uid = new Date;
    sessionStorage.setItem('sstest', uid);
    let got = sessionStorage.getItem('sstest');
    sessionStorage.removeItem('sstest');
    if (got == uid) { storage = 1; } }
  catch (e) { } 
  return storage;
}

function postRequest (path, params) 
{ 
  var form = document.createElement("form"); 
  form.setAttribute("method", "POST"); 
  form.setAttribute("action", path); 
  for (var key in params) { 
    if (params.hasOwnProperty(key)) { 
      var hiddenField = document.createElement("input"); 
      hiddenField.setAttribute("type", "hidden"); 
      hiddenField.setAttribute("name", key); 
      hiddenField.setAttribute("value", params[key]); 
      form.appendChild(hiddenField); } } 
  document.body.appendChild(form); 
  form.submit(); 
  return false;
}

function pageInit ()
{
  vuser = getLocal('uTkn') != '' ? true : false;
  if (!V['_navru'] || vpage == 'idx' || vpage == 'iru' || vpage == 'ien' || vpage == 'gui') { 
      if (document.getElementById('HEN')) { document.getElementById('HEN').style.display = 'block'; } }
  if (V['_navru'] && ven) {
      if (document.getElementById('HRU')) { document.getElementById('HRU').style.display = 'block'; } }
  if (!V['_navru']) {
    if (V['restrict'] == 'ru') {
      if (vpage = 'run') { document.location = '/'+vpath+'/'+vtest+'.html'; }
      if (vpage == 'qtl' || vpage == 'qpl') { document.location = '/en.html'; } }
    if (V['restril']) {
      for (let id of V['restril'].split(/ /)) { if (id != '') {
        document.getElementById('rra'+id).style.pointerEvents = 'none'; } } }  }
  V['_storage'] = storageCheck();  
  let engine = str(V['engine']);
  if (engine && !V['_storage']) { 
    errBox(
'В вашем браузере отключен или не поддерживается SessionStorage, тесты работать не будут (<a href="/support.html">подробнее</a>).',
'SessionStorage is disabled or not supported in your browser, so automated testing is not available.'); }
  if (vpage == 'err') {
    ven = V['_navru'] ? false : true;
    errOr(V['errtype']); }
  if (vpage == 'ind') {
    setSVar('indexref', window.frames.top.document.referrer);
    delVar('started'); }
  if (vpage == 'run') {
    delVar('started');
    runPrepare();
    studyPrepare();
    runCheck();
    if (V['_testInit']) { testInit(); } }
  if (vpage == 'bla') {
    blankFill(); }
  if (vpage == 'stu') {
    studyInit(); }
  if (vpage == 'qtl') {
    studyPrepare();
    if (V['loadstor']) { qmlLoadStor(); }
    if (V['_testBegin']) { testBegin(); V['_testBegin'] = 0; }
    qtlShow(); }
  if (vpage == 'qpl') {
    studyPrepare();
    if (!document.getElementById("qpRules")) { qplShow(); } }
  if (vpage == 'ind' || vpage == 'res') {
    if (document.getElementById('storeTagz') && document.getElementById('realTagz')) {
      document.getElementById('realTagz').appendChild(document.getElementById('storeTagz'));
      ui('realTagz'); ui('storeTagz', 'flex'); } 
    if (document.getElementById('storeMoar') && document.getElementById('realMoar')) {
      document.getElementById('realMoar').appendChild(document.getElementById('storeMoar'));
      ui('realMoar'); ui('storeMoar'); } }
  if (vpage == 'res') {
    if (V['_rated']) { msgSend('text', 'ad_rep_'+getRandomInt(1,99999)); }
    if (!ven && !V['norate'] && getVar('rate')) {
      ui('resRate');
      setLocal('uREZ', int(getLocal('uREZ'))+1); }
    let td = new Date(); td.setHours(0, 0, 0, 0);
    let rz = int(getLocal('uRZ'));
    if (getLocal('uRZD') != td) { setLocal('uRZD', td); rz = 0; }
    if (getLocal('uRZL') != document.location) { setLocal('uRZL', document.location); rz++; }
    setLocal('uRZN', rz);
    delVar('rate');
    delVar('flok'); }  
  if (vuser) {
    let tping = int(getLocal('uPing'));
    let tnow = Math.floor(new Date().getTime() / 1000);
    if (tnow - tping > 14400) { userPing(); } }
  if (vpage == 'use') {
    if (!vuser) { document.location = '/'; }
    else { userPageInit(); } }
  userIcon();
  if ((vpage == 'ind' || vpage == 'run') && document.getElementById('fStar')) { star(2); }  
}

function studyBack (mode)
{
  let bat = int(getVar('bat'));
  if (bat == 0) { bat = int(V['_bat']); }
  if (bat == 0) { return ""; }
  let batn = getVar('batn');
  if (batn == '') { batn = str(V['_batn']); }
  if (mode == 1) { return "/study.html?b="+bat+(batn != '' ? '&n='+batn : ''); }
  else { return "?bat="+bat+(batn != '' ? '&bn='+batn : ''); }
}

function studyPrepare ()
{
  let sb = studyBack(1);
  if (sb == "") { return; }      
  if (document.getElementById('uredo')) { document.getElementById('uredo').href = sb; }
  ui('pageH1', 'none');
  ui('notforbat', 'none');
  document.title = "Прохождение теста в рамках исследования";
}

function getVAge ()
{
  if (!document.getElementById("stdAgeValue")) { return 0; }
  let val = document.getElementById("stdAgeValue").innerHTML;
  if (val.match(/>\d+</)) { val = int((val.match(/>(\d+)</))[1]); }
  return val;
}

function runBegin ()
{
  if (V['paused']) {
    document.getElementById('stdRunErr').innerHTML = 'тест временно недоступен';
    errBox("По техническим причинам тест временно недоступен."); 
    return false; }
  let rref = window.frames.top.document.referrer;
  if (rref.includes('/'+vpath+'/'+vtest.substring(0,2))) { rref = getSVar('indexref'); }
  if (rref != '') { msgSend('refr', vpath+'/'+vtest+' '+encodeURI(rref)); }
  if (!V['loadstor']) { sessionStorage.clear(); }
  let engine = V['engine'];
  let setvar = V['_setvar'];
  if (setvar) { setVar(setvar, V[setvar]); }
  if (V['sex']) {
    let sex = document.getElementById("stdSexValue").innerHTML;
    if (sex != 'F' && sex != 'M') { sex = 'M'; }
    setVar('sex', sex); }
  if (V['agemax']) {
    let age = getVAge();
    if (age == null) { age = int(V['agemin']); }
    if (age < int(V['agemin'])) { age = int(V['agemin']); }
    if (age > int(V['agemax'])) { age = int(V['agemax']); }
    setVar('age', age); }
  if (V['blank'] == 'B' && document.getElementById("fpBlank")) { 
      if (document.getElementById("fpBlank").checked) { setVar('blank', 1); } } 

  if (str(V['_bat']) != '') { 
    setVar("bat", V['_bat']); 
    if (str(V['_batn']) != '') { setVar("batn", V['_batn']); }
    if (str(V['_batauth']) != '') { setVar("batauth", V['_batauth']); }
    if (str(V['_batname']) != '') { setVar("batname", V['_batname']); }
    if (str(V['_batself']) != '') { setVar("batself", V['_batself']); } }

  setVar("param", str(V['_param'])); 
  timeStart();
  if (engine == 'qtl') {
    setVar('started', V['onpage']);
    setVar('qq', 0);
    setVar('qa', 0);
    qtlShow(); }
  if (engine == 'qpl') {
    setVar('started', 1001);
    document.location = '/'+vpath+'/'+vtest+'_1.html'; } 
  if (engine == 'custom') {
    setVar('qa', "");
    if (document.getElementById('testRule')) {
      document.getElementById('testRule').style.display = 'none'; }
    if (document.getElementById('testContent')) {
      document.getElementById('testContent').style.display = 'block'; }
    window.scroll(0,0);
    if (V['_testBegin']) { testBegin(); }
  }
}

function runFinal (block)
{
  if (V['_runFinal'] == 1) { 
    return false; }
  if (!document.getElementById('stdFinal')) {
    return false; }

  let bat = int(getVar('bat'));
  let batauth = bat > 0 ? str(getVar('batauth')) : '';
  let batself = bat > 0 ? int(getVar('batself')) : 0;
  let batname = bat > 0 ? int(getVar('batname')) : 0;
  let batn =  bat > 0 ? str(getVar('batn')) : '';
  let blon = int(getVar('blank'));
  let nores = 0;

  let html = "";
  if (bat > 0 && !batself) { 
    let bval = str(getLocal('bat_'+bat+'_n'));
    html = html + '<div class="finBlock finBat"> <div> <input type="checkbox" id="fiBat" checked>' +
    '<div> <p>Результаты получит <b>' + batauth + '</b></p> </div> </div>' +
    (batn == '' && batname == 1 ? '<div class="finBatN">под именем <input type="text" id="fiCm" maxsize=20 value="'+bval+'" placeholder="анонимно"></div><div class="fprPDN">Не передавайте свои персональные данные (ФИО, контакты), если не давали согласие на&nbsp;их&nbsp;обработку указанному лицу или организации.</div>' : '') +
    '</div>'; }

  if (bat > 0 && batself == 1) { 
    html = html + '<div class="finBlock finBat"> <div> <input type="checkbox" id="fiBat" checked>' +
    '<div> <div>Сохранить под именем <input type="text" id="fiCm" maxsize=24></div>  </div>' +
    ' </div></div>'; }

  if (V['blank'] == 'B') { 
    html = html + '<div class="finBlock finBlank"> <input type="checkbox" id="fiBlank"' + (blon ? ' checked' : '') +
    '> <div>' + (ven ? 'Keep the form with your answers' :  (bat > 0 && !batself ? 'Передать' : 'Сохранить') +
    ' бланк с ответами') +' </div> </div>'; }

  if (vuser && getLocal('uKind') == 'U' && int(V['nosave']) != 1 && vtest != 'anketa') {
    html = html + '<div class="finBlock finSave"> <input type="checkbox" id="fiSave" checked>' +
    '<div>Сохранить результат в <span>личном </span>кабинете' +(bat > 0 ? '' :  
    '<span id="fiCmX"> + <a href="#" onclick="return swCm();">комментарий</a></span>' +
    '</div><div><input type="text" maxsize=20 id="fiCm" style="display: none;">') + '</div></div>'; }

  if (bat > 0 && document.getElementById('stdResButton') && !ven && vtest != 'anketa') {
    document.getElementById('stdResButton').value = 'СОХРАНИТЬ РЕЗУЛЬТАТ ТЕСТА'; }


  document.getElementById('stdFinal').innerHTML = html;
  ui('stdFinal'); 
  V['_runFinal'] = 1; 
  return true;
}

function runPrepare ()
{
  let bat = '';
  let batn = '';
  let param = '';
  let s = window.location.search;
  if (s != "" && s.charAt(0) == '?') { s = s.substring(1); } else { s = ""; }
  if (s != "" && !s.includes('=')) { param = s; s = ""; } 
  if (s != "" ) {
    s = '&' + s;
    let r1 = s.match(/\&f=([^\=\&]+)/);
    if (r1) { param = r1[1]; }
    let r2 = s.match(/\&bat=(\d+)/);
    if (r2) { bat = r2[1]; }
    let r3 = s.match(/\&bn=([^\=\&]+)/);
    if (r3) { batn = r3[1]; } }
  if (str(batn) != "") { try { let dbn = fromB64(batn); } catch (e) { return errOr('debase'); } } 
  V['_param'] = param;

  let batauth = '';
  let batself = '';
  let batrest = '';
  let batblan = '';
  let batinac = '';
  if (bat > 0) {
    let utkn = getLocal('uTkn');
    let xhr = new XMLHttpRequest();
    xhr.open('POST', '/user', false);
    xhr.send('a=gbat&b='+bat+'&f='+V['_param']+'&t='+V['code']+(utkn != '' ? '&tkn='+utkn : ''));
    if (xhr.status != 200) { bat = ''; }
    bb = xhr.responseText.trim();
    if (bb.startsWith('0|')) {
      let ba = bb.split('|');
      if (ba[1] == 'A') {
        if (document.getElementById('tVar')) { 
          if (str(V['parallel']) != '') {
            let tv = document.getElementById('tVar').innerHTML;
            document.getElementById('tVar').innerHTML =
              tv.replaceAll('-run.html"', '-run.html?bat='+bat+(batn != '' ? '&bn='+batn : '')+'"'); }
          else { ui('tVar', 'none'); ui('tVart', 'none'); ui('tVari', 'none'); } }
        ui('trInfo', 'none');
        batactv = ba[1];
        batauth = ba[2];
        batrest = ba[3].includes('R1') ? 1 : '';
        batblan = ba[3].includes('B1') ? 1 : '';
        batself = int(ba[4]);
        V['_bat'] = bat;
        V['_batauth'] = batauth;
        V['_batself'] = batself;
        V['_batrest'] = batrest;
        V['_batname'] = ba[3].includes('N1') ? 1 : '';
        V['_batn'] = batn; }
      else if (ba[1] == 'Z') { batinac = 'закрыто'; }
      else { batinac = 'недоступно'; }
      if (batinac != '') { bat = ''; }
    }
    else { bat = '';  } } 

  let html = '';

  if (bat > 0 && !batself) { 
    V['_checkbat'] = 1;
    let bval = getLocal('bat_'+bat+'_n');
    html = html + '<div class="finBlock fprBat finRed" id="fpBat"> <div> <p>Ваши результаты <span id="fpBatZ">запрашивает</span> <b>' + batauth + '</b></p> </div>' +
'<div id="fpBatX"><div onclick="swSend(1);">Предоставить</div> <div onclick="swSend(0);">Отказаться</div> </div>';
    html = html + '<div class="fprPDN">Не передавайте свои персональные данные (ФИО, контакты), если не давали согласие на&nbsp;их&nbsp;обработку указанному лицу или организации.</div>'; 
    if (batrest && vtest != 'anketa') {
      html = html + '<div class="fpBatNR">По условиям исследования вы не увидите результаты теста.</div>'; }
    html = html + '</div>'; }

  if (bat > 0 && batself) { 
  html = html + '<div class="finBlock fprSelf">Результат теста будет сохранен в рабочем кабинете.</div>'; }

  if (bat > 0 && document.getElementById('orgorg')) { document.getElementById('orgorg').innerHTML = batauth; }

  if (batinac != '') { 
  html = html + '<div class="finBlock fprSelf">Исследование, на которое вы перешли, ' + batinac + ', но сам тест можно пройти.</div>'; }

  if (V['blank'] == 'B') {
  html = html + '<div class="finBlock fprBlank"> <div> <input type="checkbox" id="fpBlank"'+(batblan == 1 ? ' checked' : '') +
  ' onclick="swBlan(2,\''+bat+'\')">' + '<div id="fpBlS">' + (ven ? 'Keep the form with your answers' : 
   (bat > 0 && !batself ? 'Передать' : 'Сохранить') + ' бланк с ответами.') +
'</div> <a id="fpBlA" href="#" onclick="return swBlan(3,\''+bat+'\');"><div class="iREM"></div></a> </div>' +
'<div id="fpBlW" style="display: none;">' + (ven ?
'<p>Along with the report you will get the completed form with your answers. '+
'<b>Please be cautious:</b> your&nbsp;answers will be visible to anyone who have your Report+Form link. '+
'We recommend sharing link to the Report only (without the form), which will also be available.</p>'
 : '<p>Вместе с результатом будет сохранен заполненный бланк теста с вашими ответами.</p>'+
'<p id="fpBlU"><b>Внимание:</b> ваши ответы будут видны любому человеку, получившему ссылку на результат с бланком. '+
'Ссылка на результат теста без бланка также будет доступна, рекомендуется делиться только ей.</p>') +
'<div id="fpBlX"><div onclick="swBlan(1,\''+bat+'\');">' + (ven ? 'Yes, sure' : 'Да, понятно') + 
'</div> <div onclick="swBlan(0,\''+bat+'\');">' +
   (ven ? 'No, thanks' : 'Не сохранять') + '</div> </div></div></div>'; }

  document.getElementById('stdRunPrepare').innerHTML = html; 
  if (bat == '' && document.getElementById('fpBlU')) { ui('fpBlU', 'block'); }
  if (batblan) { swBlan(2); }
  if (vuser && str(V['sex']) != '' && document.getElementById('stdSexSelector')) {
    let usex = getLocal('uSex');
    if (usex == 'M' || usex == 'F') { runSexClick(usex); } }
  if (vuser && int(V['agemax']) > 0 && int(V['agemod']) != 3 && document.getElementById('stdAgeSelector')) {
    let uage = int(getLocal('uAge'));
    if (uage > 0 && uage >= int(V['agemin']) && uage <= int(V['agemax'])) { 
      document.getElementById("stdAgeValue").innerHTML = uage; } }
}

function swBlan (v,bat)
{
  if (!document.getElementById('fpBlank')) { return false; }
  if (v == 0) { 
    document.getElementById('fpBlank').checked = false; 
    setLocal('uBlankOk'+str(bat), 1); }
  if (v == 1) { 
    document.getElementById('fpBlank').checked = true; 
    setLocal('uBlankOk'+str(bat), 1); }
  if (v == 0 || v == 1) { 
    ui('fpBlW', 'none'); }
  if (v == 2 && !getLocal('uBlankOk'+str(bat))) { 
    ui('fpBlW', document.getElementById('fpBlank').checked ? 'block' : 'none'); }
  if (v == 3) { 
    ui('fpBlW', uinone('fpBlW') ? 'block' : 'none'); } 
  return false;
}

function swSend (v) 
{
  if (v == 0) {
    V['_bat'] = '';
    V['_batauth'] = '';
    ui('fpBat', 'none');
    if (document.getElementById('fpBlS')) { document.getElementById('fpBlS').innerHTML = 'Сохранить бланк с ответами.'; }
    ui('fpBlU', 'block'); 
/*    if (V['_batrest'] == '1') { */
    document.getElementById('stdRunErr').innerHTML = 'вы отказались от прохождения теста'; 
/* }  else { V['_checkbat'] = 0; runCheck(); } */
  } else {
    document.getElementById('fpBat').className = 'finBlock fprBat'; 
    document.getElementById('fpBatZ').innerHTML = 'получит';
    ui('fpBatX', 'none'); 
    V['_checkbat'] = 0;
    runCheck(); }
}


function swBl (v) {
  if (v == 1) { 
    document.getElementById('fpBlA').style.display =
      document.getElementById('fpBlA').style.display == 'none' ? ' block' : 'none'; }
  if (v == 2) { 
    if (document.getElementById('fpBlX').innerHTML == '') {
      document.getElementById('fpBlX').innerHTML = ven ?
'<p>If this box is checked, along with the report you will get the completed form with your answers. '+
'<b>Please be cautious:</b> your&nbsp;answers will be visible to anyone who have your Report+Form direct link. '+
'We recommend sharing link to the Report only (without the form), which will also be available.</p>'
  : '<p>Если галочка установлена, вместе с результатом вы получите заполненный бланк теста с вашими ответами. '+
'<b>Будьте осторожны:</b> ваши ответы будут видны любому человеку, получившему ссылку на результат с бланком. '+
'Ссылка на результат теста без бланка также будет доступна, рекомендуется делиться только ей.</p>'; } }
 return false;
}

function swCm () {
  document.getElementById('fiCm').style.display = 'block';
  document.getElementById('fiCmX').style.display = 'none';
  return false; }

function runResult ()
{
  let elapsed = Math.floor(new Date().getTime() / 1000) - int(getVar('start')); 
  setVar('rate', 1);
  setVar('flok', 1);

  let uu = vuser ? getLocal('uTkn') : '';
  let bb = getVar('bat');
  if (document.getElementById('fiBat')) { if (!document.getElementById('fiBat').checked) { bb = ''; } }
  let cc = '';
  if (int(bb) > 0) {
    let batn = str(getVar('batn'));
    cc = batn;
    if (cc != '') { setSVar('bn'+bb, cc); cc = fromB64(cc); }
    if (cc == '' && document.getElementById('fiCm')) { 
      cc = document.getElementById('fiCm').value; 
      if (cc == 'анонимно') { cc = ''; } 
      if (int(getVar('batself')) == 0) { setLocal('bat_'+bb+'_n', cc); } } }
  else {
    if (document.getElementById('fiCm')) { cc = document.getElementById('fiCm').value; } }
  if (cc != '') { cc = cc.replaceAll(/[\<\>\"\\]/g, ''); } 
  let ss = 0;
  if (document.getElementById('fiSave') && vuser && getLocal('uKind') == 'U') {
    if (document.getElementById('fiSave').checked) { ss = 1; } }
  let aa = int(bb) > 0 ? userAnon() : '';

  if (int(bb) > 0) {
    let gl = getLocal('batDone'+bb);
    if (!gl.includes(V['code']+'_')) { setLocal('batDone'+bb, gl+V['code']+'_'); } }

  let query = getVar('query');
  if (query != '') {
    let code3 = V['code'].substring(0,3);
    let genu = code3 == 'szo' ? getVar('szondy') : '';
    postRequest('/post/', { 
     'r': 'result',
     'c': code3 ,
     'q': str(V['code'].substring(3,4)) + query,
     's': str(getVar('sex')),
     'a': str(getVar('age')),
     'f': str(getVar('param')),
     't': elapsed,
     'uu': uu,
     'cc': cc,
     'bb': bb,
     'ss': ss,
     'aa': aa,
     'g': genu } );
    return true; }

  let engine = V['engine'];
  let qa = getVar('qa');

  if (engine == 'qtl') {
    if (qa.length - 1 != int(V['qtotal'])) {
      return errOr('fatal', 'web/qa'+qa+'!='+V['qtotal']); }
    if (V['qml']) {
      qa = "0";
      let sep = V['qtlkey'] ? '' : "|";
      for (ii = 1; ii <= int(V['qtotal']); ii++) {
        qa = "" + qa + sep + str(getVar('qm'+ii)); } } 
    if (V['_testResult']) { qa = testResult(); }
  }

  let bl = str(getVar('blank'));
  if (document.getElementById('fiBlank')) { bl = document.getElementById('fiBlank').checked ? 1 : 0; }
  if (V['blank'] == 'F') { bl = 1; }

  postRequest('/post/', { 
   'r': 'result',
   'o': vtest,
   'w': qa,
   's': str(getVar('sex')),
   'a': str(getVar('age')),
   'f': str(getVar('param')),
   'bl': bl,
   'uu': uu,
   'cc': cc,
   'bb': bb,
   'ss': ss,
   'aa': aa,
   't': elapsed } );
  return true;
}

function runQuery (query) 
{
   setVar('query', query);
   if (int(V['nosave']) != 1 && int(V['_noFinal']) != 1 && document.getElementById('testCustomRes')) {
     if (uinone('testCustomRes')) {
       runFinal();
       if (document.getElementById('testContent')) {
         document.getElementById('testContent').style.display = 'none'; }
       document.getElementById('testCustomRes').style.display = 'block';
       return false; } } 
   runResult();
}

function errBox (tru, ten)
{
  document.getElementById('errBox').className = 'errBox';
  document.getElementById('errBox').innerHTML = ven ? ten : tru;
}

function errPage (tru, ten)
{
  document.getElementById('pageContent').innerHTML = '<div class="errPage"><div>'+(ven ? ten : tru)+'</div></div>';
}

function errOr (mode, err)
{
  if (mode == '404') {
    errBox('Страница не найдена.', 'Page is not found.'); }
  else if (mode == 'result') {
    errBox('Страница результата не найдена.', 'The result page is not found.'); }
  else if (mode == 'ankopen' || mode == 'anketa') {
    errBox('Данные недоступны'); }
  else {
    errBox('Что-то пошло не так...', 'Something went wrong...'); }
  
  if (document.getElementById('pageHdr')) {
    document.getElementById('pageHdr').style.display = 'none'; }
  if (document.getElementById('pageFooter')) {
    document.getElementById('pageFooter').style.display = 'none'; }

  if (mode == '404') {
    errPage('<p>Ошибка 404. Запрошенная страница не найдена.</p>', '<p>Error 404. The requested page is not found.</p>'); } 

  else if (mode == 'result') {
    errPage('<p>Некорректная ссылка на результат теста.</p><br><p>Частые причины возникновения этой ошибки:</p>'+
'<p>&bull; потерялся последний символ в ссылке;</p><p>&bull; к ссылке прилипли лишние символы;</p>'+
'<p>&bull; ссылка переведена в нижний регистр.</p>', '<p>Link to the result is incorrect.</p>'); }

  else if (mode == 'debase') {
    errPage('<p>Некорректная ссылка на исследование.</p><br><p>Скорее всего почтовый интерфейс или мессенджер обрезал в ссылке последний символ: плюс или двоеточие.</p>'+
'<p>Скопируйте ссылку полностью в адресную строку, или просто допишите потерянный символ.</p>'); }

  else if (mode == 'started') {
    errPage('<p>Тест не стартовал должным образом.</p>'+
'<p>Если вы попали сюда из поисковика или по прямой ссылке, ничего страшного – просто перейдите на страницу теста:</p>'+
'<br><div class="tl xbl c"><div><a id="errt" href="/'+vpath+'/'+vtest+'.html"></a></div></div><br><p>Если же вы попали сюда во время прохождения теста'+
' – сожалеем: произошел какой-то сбой, ваши промежуточные ответы были повреждены или не сохранились. Попробуйте <a href="/'+vpath+'/'+vtest+'-run.html">'+
'начать тест сначала</a>, посмотрите <a href="/support.html">возможные причины</a> неполадок.</p>',
'<p>The test didn\'t started the right way.</p>'+
'<p>If you\'re occasionally got here from search engine or by direct link, it\'s not a problem – just go to the test page:</p>'+
'<br><div class="tl xbl c"><div><a id="errt" href="/'+vpath+'/'+vtest+'.html"></a></div></div><br><p>If you\'re got here while assessing the test'+
' – there is some problem with intermediate storage of your answers, they got lost or corrupted.'+
'</p><p>You&nbsp;may try to <a href="/'+vpath+'/'+vtest+'-run.html">'+'restart test again</a>, it\'s the only solution, sorry.</p>'); 
    document.getElementById('errt').innerHTML = document.getElementById('pageH1').innerHTML; }

  else if (mode == 'stor') {
    errPage('<p>Ошибка: ответы респондента не были загружены.</p>'+
'<p>Обратите внимание: оценка ответов может быть запущена только со страницы протокола ответов нажатием на кнопку «Оценить ответы». '+
'Переходы по прямым сслыкам приводят к ошибке. Попробуйте еще раз: откройте протокол ответов и нажмите кнопку.</p>'+
'<p>Если ошибка повторяется – проверьте корректность ссылки на протокол. Возможные причины проблемы:</p><p>&bull; потерялся последний символ в ссылке;</p>'+
'<p>&bull; к ссылке прилипли лишние символы;</p><p>&bull; ссылка переведена в нижний регистр.</p>'); }

  else if (mode == 'ankopen') {
    errPage("Анкета удалена, либо у вас недостаточно прав для просмотра."); }
  else if (mode == 'anketa') {
    errPage("Неверная ссылка, либо анкета удалена или временно отключена."); }

  else { 
    errPage('<p>Сожалеем, произошла критическая ошибка в процессе прохождения теста.</p>'+
'<p>Ваши промежуточные ответы были повреждены или не сохранились.</p><p>Попробуйте <a href="/'+vpath+'/'+vtest+'-run.html">'+
'начать тест сначала</a>, посмотрите <a href="/support.html">возможные причины</a> неполадок.</p>',
'<p>Fatal error has happened.</p>'+
'<p>There is some problem with intermediate storage of your answers, they got lost or corrupted.</p>'+
'<p>You may try to <a href="/'+vpath+'/'+vtest+'-run.html">'+'restart test again</a>, it\'s the only solution, sorry.</p>'); }

  if (err) { msgSend('error', err); }
  return false;
}

function errServer (e)
{
if (e == 1001) { return 'Выберите тип аккаунта'; }
else if (e == 1010) { return 'Введите логин'; } 
else if (e == 1011) { return 'Недопустимые символы в логине. Допустимы латинские буквы, цифры, символы !@$%&*_-+=:.'; }
else if (e == 1012) { return 'Пробелы в логине недопустимы'; }
else if (e == 1013) { return 'Такой логин уже существует'; }
else if (e == 1014) { return 'Логин или пароль введены неверно'; }
else if (e == 1015) { return 'Аккаунт заблокирован'; }
else if (e == 1016) { return 'Пароль введен неверно'; }
else if (e == 1017) { return 'Логин не может состоять только из цифр'; }
else if (e == 1018) { return 'Извините, символ @ в логине не допускается'; }
else if (e == 1020) { return 'Введите пароль'; }
else if (e == 1021) { return 'Недопустимые символы в пароле. Допустимы латинские буквы, цифры, символы'; }
else if (e == 1022) { return 'Пробелы в пароле недопустимы'; }
else if (e == 1023) { return 'Задайте пароль длиннее четырех символов'; }
else if (e == 1024) { return 'Повторите пароль'; }
else if (e == 1025) { return 'Пароли не совпадают'; }
else if (e == 1026) { return 'Введите старый пароль'; }
else if (e == 1030) { return 'Не указан адрес электронной почты'; }
else if (e == 1031) { return 'Некорректный адрес электронной почты'; }
else if (e == 1032) { return 'Этот адрес электронной почты уже использован'; }
else if (e == 1033) { return 'Слишком длинный адрес электронной почты'; }
else if (e == 1034) { return 'Логин или почта указаны неверно'; }
else if (e == 1035) { return 'Вы уже запросили восстановление пароля, проверьте почту'; }
else if (e == 1036) { return 'Ссылка на смену пароля недействительна'; }
else if (e == 1037) { return 'Логин введен неверно'; }
else if (e == 1038) { return 'Письмо с подтверждением уже отправлено, проверьте почту'; }
else if (e == 1039) { return 'Подтверждение не запрашивалось'; }
else if (e == 1040) { return 'Введите проверочный код с картинки'; }
else if (e == 1041) { return 'Проверочный код введен неверно'; }
else if (e == 1042) { return 'Неверная ссылка на подтверждение почты'; }
else if (e == 1050) { return 'Подтвердите согласие с условиями и политиками сайта'; }
else if (e == 1051) { return 'Дайте согласие на обработку персональных данных'; }
else if (e == 1101) { return 'Организатор исследования должен быть указан.'; }
else if (e == 1102) { return 'Название исследования должно быть заполнено.'; }
else if (e == 1103) { return 'Ссылка на тест указана неверно.'; }
else if (e == 1104) { return 'Этот тест уже есть в исследовании.'; }
else if (e == 1201) { return 'Исследование закрыто.'; }
else if (e == 1202) { return 'Исследование недоступно.'; }
else if (e == 1203) { return 'Данные не найдены.'; }
else if (e == 1204) { return 'У вас нет прав на просмотр этого объекта.'; }

else if (e == 1400) { return 'Ошибка соединения с сервером, попробуйте повторить операцию позже'; }
else if (e > 1400 && e < 1500) { return 'Ошибка на сервере, попробуйте повторить операцию позже'; }
return '';
}


function qtlShow ()
{
  let qa = getVar('qa');
  let qq = int(getVar('qq'));
  let sex = V['sex'] == 'FM' ? getVar('sex') : '';

  qq++;
  V['_qq'] = qq;

  let err = '';
  let qtotal = int(V['qtotal']);
  let onpage = int(V['onpage']);
  let started = int(getVar('started'));
 
  if (!started) { return errOr('started'); }
  if (started != onpage) { return errOr ('started', 'web/started/'+started+'!='+onpage); }
  if (qq > qtotal + 1) { err = 'qq'+qq+'>'+qtotal; }
  if (qa.length != qq) { err = 'qa'+qa+'!='+qq; }
  if (V['sex'] == 'FM' && sex != 'F' && sex != 'M') { err = 'sex'+sex+'!=FM'; }
  if (err) { return errOr ('fatal', 'web/fatal/'+err); }

  let qlast = qq > qtotal ? qtotal : qq;
  let qfile = 1 + Math.floor((qlast-1)/onpage); 
  if (int(V['qfile']) != qfile) {
    document.location = '/'+vpath+'/'+vtest+sex+'_'+qfile+'.html';
    return; }

  if (qq <= qtotal) { 
    ui('qtlResult', 'none');
    ui('qtlBlock'+qq);
    if (V['_qtlCustomPaint'] == 1) { qtlCustomPaint(qq); }
    if (V['qml']) { 
      if (V['qm'+qq+'-type'] == 'answer') { ui('qmlNext', 'none'); } else { ui('qmlNext'); } } } 
  else if (int(V['nosave']) == 1) {
    document.getElementById('stdResButton').click(); }
  else {
    ui('qtlResult');
    runFinal();
    if (V['qml']) { ui('qmlNext', 'none'); } }
  ui('qtlBlock'+(qq-1), 'none');

  document.getElementById('pageBody').scrollIntoView();

  if (document.getElementById('qmlSupl0') && document.getElementById('supl'+qq)) {
    document.getElementById('qmlSupl0').innerHTML = document.getElementById('supl'+qq).innerHTML; }

  if (document.getElementById('qHB'+qq)) { 
    qtlHideOnOff(qq, 0);                               
    window.scrollTo(0,0); }

  if (document.getElementById('qtlQRule'+qq)) {
    if (document.getElementById('qtlQRule'+qq).innerHTML != "") {
      document.getElementById('qtlQRule'+qq).style.display = 'block'; } } 

  var pc = Math.round(((qq-1)/qtotal)*100);
  document.getElementById('qtlMeterLine').style.width = "" + pc + '%';
  document.getElementById('qtlMeterLine').innerHTML = '<span class="qtlMeterText">'+(ven ? 'Item' : 'Вопрос')
    +'&nbsp;'+qlast+'&nbsp;'+(ven ? 'from' : 'из')+'&nbsp;'+qtotal+'&nbsp;('+pc+'%)</span>';

  if (document.getElementById('rmst')) {
    if (document.getElementById('rmst').style.display == 'block') { fixMistake(1); } }
  if (V['qml']) { qmlCheck(qq); }
  V['_ready'] = 1;
  if (V['qml']) {
    let qe = int(V['qempty']);
    if (qe != 0 && document.getElementById('stor_'+qq)) {
      if (document.getElementById('stor_'+qq).innerHTML == '') {
        qmlClick(qq, qe, 1); 
        qtlAnswer(-1, 1); } } }

  if (int(V['skip-q-'+qq]) == 1) { if (getVar('_goback') == 1) { qtlGoBack(); } else { qtlAnswer(qq, 1); } }
  delVar('_goback');
}

function qtlUnWrap (qnum)
{
  document.getElementById('qtlQRule'+qnum).innerHTML = "";
  document.getElementById('qtlQWrap'+qnum).style.display = 'block';
}

function qtlAnswer (qnum, qansw)
{
  if (!V['_ready']) { return; }
  V['_ready'] = 0;
  let qn = int(qnum);
  if (qn == -1) { qn = int(getVar('qq')) + 1; }
  let qa = getVar('qa');
  let qq = int(getVar('qq'));
  if (qq == qn - 1 && qa.length == qn) {
    if (qansw >= 10) { qansw = String.fromCharCode(qansw + 55); }
    setVar('qa', "" + qa + qansw);
    setVar('qq', qn); }
  if (document.getElementById('qtlQ'+qn+'A'+qansw)) { 
    document.getElementById('qtlQ'+qn+'A'+qansw).disabled = false; }
  qtlShow();
}

function qtlGoBack ()
{
  if (!V['_ready']) { return; }
  V['_ready'] = 0;
  let qa = getVar('qa');
  let qq = int(getVar('qq'));
  if (qq < 1) {
    document.location = '/'+vpath+'/'+vtest+'-run.html'+studyBack(0);
    return; }
  if (qq < int(V['qtotal'])) {
    if (document.getElementById('qtlBlock'+qq)) {
      document.getElementById('qtlBlock'+(qq+1)).style.display = 'none'; } }
  qq--;
  qa = qa.substring(0, qa.length-1);
  setVar('qa', qa);
  setVar('qq', qq);
  setVar('_goback', 1);
  qtlShow();
}

function qplShow () 
{
  let ph = int(V['phase']);
  let st = int(getVar('started'));
  let timeron = int(V['limit']) > 0 && int(getVar('nolimit')) == 0 ? 1 : 0;
  if (st < 1000) {
    return errOr('started'); }
  else if (st < 2000) {
    if (st != 1000 + ph) {
      document.location = '/'+vpath+'/'+vtest+'_'+str(st-1000)+'.html'; } }
  else if (st <= 3000 && timeron) {
    qplNotime();
    return; }
  if (ph == 1) { timeStart(); }
  for (ii = 1; ii <= V['qtotal']; ii++) { V['p'+ph+'qm'+ii] = ''; }
  if (V['_testShow']) { testShow(ph); }
  document.getElementById("qpPanel").style.display = 'block';
  document.getElementById("qpResult").style.display = 'block';
  if (document.getElementById("qpRules")) {
    document.getElementById("qpRules").style.display = 'none'; }
  if (document.getElementById("qpTest")) {
    document.getElementById("qpTest").style.display = 'block'; }
  if (timeron) {
    document.getElementById('qplTimer').style.display = 'block';
    V['_timer'] = Math.floor(new Date().getTime() / 1000);
    qplTick(); }
  let hh = int(document.getElementById('qpPanel').clientHeight);
  document.getElementById('qpResult').style.paddingBottom = str(hh+20)+'px';
  if (document.getElementById("qpRule")) {
    document.getElementById('qpRule').scrollIntoView(); }
  else { 
    document.getElementById('qpBlock1').scrollIntoView(); } 
  if (V['aall']) { qplCheckAll(); }
  else { frmEnable('Res', 1); }
  setVar('started', 2000+ph);
}

function qplTick() 
{ 
  let now = Math.floor(new Date().getTime() / 1000); 
  let val = int(V['_timer']) + int(V['limit']) - now;
  if (val <= 0) {
    setVar('started', 3000);
    qplNotime();
    return false; }
  else {
    document.getElementById("qplTimer").innerHTML = timeElapsed(val);  }
  if (val >= 0 && val < 60) {
    var clr = 255 - (val*5);
    document.getElementById("qplTimer").style.color = "rgb("+clr+", 0, 0)"; }
  setTimeout('qplTick()', 1000); 
}

function qplNotime () 
{
  document.getElementById("qpTest").style.display = 'none';
  document.getElementById("qpPanel").style.display = 'none';
  document.getElementById("qpResult").style.display = 'block';
  if (document.getElementById("qpRules")) {
    document.getElementById("qpRules").style.display = 'none'; }
  document.getElementById("qpNoTime").style.display = 'block';
}

function qplMark (qnum)
{
  document.getElementById("qpLink"+qnum).className = "qp2"; 
  document.getElementById("qpHeader"+qnum).className = "qpHeader qp2"; 
  document.getElementById("qpHeaderMark"+qnum).style.display = 'none'; 
  document.getElementById("qpHeaderMarked"+qnum).style.display = 'block'; 
  return false;
}

function qplCheckAll ()
{
  let isall = 1;
  let ph = int(V['phase']);
  for (ii = 1; ii <= V['qtotal']; ii++) {
    if (getVar('p'+ph+'qm'+ii) == '') { isall = false; } }
  frmEnable('Res', isall, (ven ? 'please answer each question' : 'дайте ответы на все вопросы'));
}

function qplResult ()
{
  let ph = int(V['phase']);
  let r = '';
  for (ii = 1; ii <= V['qtotal']; ii++) {
    r = "" + r + '|' + str(getVar('p'+ph+'qm'+ii)); }
  setVar('p'+ph+'r', r);
  if (V['_testResult']) { if (!testResult(ph)) { return; }; }
  let auto = str(V['automata']) != '' && int(getVar('automa')) == 0 && ph + 1 == int(V['automata']) ? true : false;
  if (ph == V['qphase'] || auto) {
    let qa = '0';
    for (ii = 1; ii <= V['qphase']; ii++) {
      qa = "" + qa + str(getVar('p'+ii+'r')); }
    if (str(getVar('nolimit')) != '') {
      qa = "" + qa + '|' + (int(getVar('nolimit')) == 1 ? 1 : 0); }
    if (str(getVar('automa')) != '') {
      qa = "" + qa + '|' + (int(getVar('automa')) == 1 ? 1 : 0); }
    setVar('qa', qa);
    if (V['_testResult']) { if (!testResult(0)) { return; }; }
    frmEnable('Res', 1);
    runResult();
  } else {
    ph++;
    setVar('started', 1000 + ph);
    document.location = '/'+vpath+'/'+vtest+'_'+ph+'.html'; } 
}

function qplAutofill (ph, field, def)
{
  let ans = getVar('p'+ph+'r');
  let fld = str(field) == '' ? 'qmp' : field;
  def = str(def);
  let ii = 0;
  for (a of ans.split(/\|/)) {
    if (ii > 0 && ii <= V['qtotal']) {
      if (document.getElementById(""+fld+ii)) {
        document.getElementById(""+fld+ii).innerHTML = a; }
      if (def && str(a) == '') { 
        document.getElementById('qpBlock'+ii).style.display = 'none';
        qmlClick(ii, def, 1); } } 
    ii++; }
}

function qmlClick (qnum, anum, val)
{
  let tp = V['qm'+qnum+'-type'];
  let an = int(V['qm'+qnum+'-an']);
  let dvl = '';
  if (tp == 'select') { 
    let mn = int(V['qm'+qnum+'-min']);
    let mx = int(V['qm'+qnum+'-max']);
    for (ii = 1; ii <= an; ii++) {
      let o = document.getElementById('qm'+qnum+'x'+ii);
      if (mn == 1 && mx == 1) { if (ii == anum) { o.className = 'qmsel'; } else { o.className = ''; } }
      else if (mn == 0 && mx == 1) { if (ii == anum) { if (o.className == 'qmsel') { o.className = ''; }  else { o.className = 'qmsel'; } } else { o.className = ''; } }
      else if (ii == anum) { if (o.className == 'qmsel') { o.className = ''; } else { o.className = 'qmsel'; } } 
    } }
  else if (tp == 'answer') {
    dvl = anum; }
  else if (tp == 'slider') {
    dvl = document.getElementById('qmt'+qnum).value; }
  else if (tp == 'imagemap' || tp == 'imagemaptext') {
    dvl = qmlImageMap(qnum, anum, val); }
  else if (tp == 'selectpm') {
    for (ii = 1; ii <= an; ii++) {
      let o = document.getElementById('qm'+qnum+'x'+ii);
      if (o.className == 'qmpmp' && val == 1 && ii != anum) { o.className = ""; }
      if (o.className == 'qmpmm' && val == 0 && ii != anum) { o.className = ""; }
      if (ii == anum && val == 1) { o.className = 'qmpmp'; }
      if (ii == anum && val == 0) { o.className = 'qmpmm'; } } }
  else if (tp == 'button') {
    for (ii = 1; ii <= an; ii++) {
      let o = document.getElementById('qm'+qnum+'x'+ii);
      if (o.className == 'qmbsel' && ii != anum) { o.className = ""; }
      if (ii == anum) { o.className = 'qmbsel'; } }
    dvl = anum; }
  else if (tp == 'brange') {
    let mn = int(V['qm'+qnum+'-min']);
    let mx = int(V['qm'+qnum+'-max']);
    let ii = 0;
    for (jj = mn; jj <= mx; jj++) {
      ii++;
      let o = document.getElementById('qm'+qnum+'x'+anum+'x'+ii);
      if (o.className == 'qmbrsel' && ii != val) { o.className = ""; }
      if (ii == val) { o.className = 'qmbrsel'; } }
    dvl = anum; }
  else if (tp == 'word') {
    for (ii = 1; ii <= an; ii++) {
      let o = document.getElementById('qm'+qnum+'x'+ii);
      if (o.className == 'qmwsel' && ii != anum) { o.className = ""; }
      if (ii == anum) {
        if (document.getElementById('qmp'+qnum)) { document.getElementById('qmp'+qnum).innerHTML = o.innerHTML; } 
        o.className = 'qmwsel'; } }
    dvl = anum; }
  qmlCheck (qnum, dvl); 
  return false;
}

function qmlCheck (qnum, dvl)
{
  let tp = V['qm'+qnum+'-type'];
  let ok = 0;
  let vl = "";
  let okerr = "";
  if (tp == 'select') {
    let an = int(V['qm'+qnum+'-an']);
    let mn = int(V['qm'+qnum+'-min']);
    let mx = int(V['qm'+qnum+'-max']);
    let zk = int(V['qmzk']);
    let t = "";
    let tnz = "";
    for (ii = 1; ii <= an; ii++) {
      let o = document.getElementById('qm'+qnum+'x'+ii);
      if (o.className == 'qmsel') { 
        let aa = ii > 9 ? String.fromCharCode(ii + 55) : ii;
        t = "" + t + (zk == 1 ? "1" : aa);
        tnz = "" + tnz + aa; }
      else if (zk == 1) { t = "" + t + '0'; } }
    if (tnz.length >= mn && tnz.length <= mx) { ok = 1; vl = t; }
    if (tnz.length > mx) { okerr = 'слишком много ответов'; } }
  else if (tp == 'answer') {
    let t = "";
    let an = int(V['qm'+qnum+'-an']);
    let zk = int(V['qmzk']);
    for (ii = 1; ii <= an; ii++) {
      if (ii == dvl) {
        let aa = dvl > 9 ? String.fromCharCode(dvl + 55) : dvl;
        t = "" + t + (zk == 1 ? "1" : aa); }
      else if (zk == 1) { t = "" + t + '0'; } }
    vl = t; ok = 1; }
  else if (tp == 'range') {
    let an = int(V['qm'+qnum+'-an']);
    let mn = int(V['qm'+qnum+'-min']);
    let mx = int(V['qm'+qnum+'-max']);
    let un = int(V['qm'+qnum+'-uniq']);
    let t = '';
    let s = 0;
    let tok = 1;
    let tu = '';
    for (ii = 1; ii <= an; ii++) {
      let o = document.getElementById('qm'+qnum+'x'+ii);
      let v = int(o.options[o.selectedIndex].value);
      if (v == 0 && mn > 0) { tok = 0; } 
      s = s + v;
      if (v > 9) { v = String.fromCharCode(v + 55); }
      if (un && tu.indexOf(v) < 0) { tu = "" + tu + v; }
      t = "" + t + str(v); }
    let ss = int(V['qm'+qnum+'-sum']);
    if (ss > 0 && s != ss) { if (s > 0) {
      let rts = s; let rtss = ss;
      if (V['qm'+qnum+'-pct']) { rts = rts*10; rtss = rtss*10; }
      okerr = 'сумма: ' + rts + ', должна быть ' + rtss; } }
    else if (tok != 1) { }
    else if (un && tu.length != mx - mn + 1) { okerr = ven ? 'each score can be assigned only once' : 'каждое значение должно быть использовано только один раз'; }
    else { ok = 1; vl = t; } }

  else if (tp == 'brange') {
    let an = int(V['qm'+qnum+'-an']);
    let mn = int(V['qm'+qnum+'-min']);
    let mx = int(V['qm'+qnum+'-max']);
    let un = int(V['qm'+qnum+'-uniq']);
    let t = '';
    let s = 0;
    let tok = 1;
    let tu = '';
    let tuok = 1;
    for (ii = 1; ii <= an; ii++) {
      let v = -1;
      let kk = 0;
      for (vv = mn; vv <= mx; vv++) {
        kk++;
        let o = document.getElementById('qm'+qnum+'x'+ii+'x'+kk);
        if (o.className == 'qmbrsel') { v = vv; break; }
      }
      if (v == -1) { tok = 0; } 
      s = s + v;
      if (v > 9) { v = String.fromCharCode(v + 55); }
      if (un) { if (tu.indexOf(v) < 0) { tu = "" + tu + v; } else { tuok = 0; } }
      t = "" + t + str(v); }
    let ss = int(V['qm'+qnum+'-sum']);
    if (ss > 0 && s != ss) { if (s > 0) {
      let rts = s; let rtss = ss;
      if (V['qm'+qnum+'-pct']) { rts = rts*10; rtss = rtss*10; }
      okerr = 'сумма: ' + rts + ', должна быть ' + rtss; } }
    else if (tok != 1) { }
    else if (un && !tuok) { okerr = ven ? 'each score can be assigned only once' : 'каждое значение должно быть использовано только один раз'; }
     else { ok = 1; vl = t; } } 

  else if (tp == 'selectpm') {
    let an = int(V['qm'+qnum+'-an']);
    let p = '';
    let m = '';
    for (ii = 1; ii <= an; ii++) {
      let o = document.getElementById('qm'+qnum+'x'+ii);
      if (o.className == 'qmpmp') { p = "" + p + ii; }
      if (o.className == 'qmpmm') { m = "" + m + ii; } }
    if (p.length == 1 && m.length == 1) { ok = 1; vl = "" + p + m; } }
  else if (tp == 'button') {
    vl = dvl; ok = 1; }
  else if (tp == 'word') {
    vl = dvl; ok = 1; }
  else if (tp == 'imagemap') {
    if (str(dvl) != "") { vl = dvl; ok = 1; } }
  else if (tp == 'imagemaptext') {
    let txt = document.getElementById('qmt'+qnum).value;
    txt = txt.replaceAll('|', '');
    txt = txt.replaceAll('<', '');
    txt = txt.replaceAll('>', '');
    txt = txt.trim(); 
    if (str(dvl) != "") { V['qmlimt'+qnum] = dvl; }
    if (txt != "" && str(V['qmlimt'+qnum]) != '') { vl = str(V['qmlimt'+qnum]) + "," + txt; ok = 1; } }
  else if (tp == 'texts' || tp == 'unfin') { 
    let an = int(V['qm'+qnum+'-an']);
    let tmin = int(V['qm'+qnum+'-min']);
    let subt = V['qm'+qnum+'-sub'];
    let res = '';
    let xmin = 0;
    for (ii = 1; ii <= an; ii++) {
      let txt = document.getElementById('qmt'+qnum+'x'+ii).value;
      txt = txt.replaceAll('|', '');
      txt = txt.replaceAll('<', '');
      txt = txt.replaceAll('>', '');
      if (subt == 'any') {
        txt = txt.trim(); }
      if (txt != '') { xmin++; }
      res = "" + res + (ii == 1 ? '' : '|') + txt; }
    ok = 1;
    if (tmin > 0 && xmin < tmin) { ok = 0; }
    if (ok == 1) { vl = res; } }
  else if (tp == 'text') { 
    let subt = V['qm'+qnum+'-sub'];
    let txt = document.getElementById('qmt'+qnum).value;
    txt = txt.replaceAll('|', '');
    txt = txt.replaceAll('<', '');
    txt = txt.replaceAll('>', '');
    if (txt.trim() == '') { txt = ''; }
    let repl = 0;
    let repvl = '';
    if (subt == 'decimal') {
      txt = txt.replace(/\D/g, ''); repl = 1; repvl = txt; }
    else if (subt == 'ruword') {
      txt = txt.toUpperCase();
      txt = txt.replace(/[^А-ЯЁ\d]/g, ''); repl = 1; repvl = txt; }
    else if (subt == 'rutext') {
      txt = txt.toUpperCase();
      txt = txt.replace(/[^А-ЯЁ\d -\.,\/]/g, ''); repl = 1; repvl = txt; }
    else if (subt == 'any') {
      txt = txt.trim(); }
    else if (subt == 'number') {
      txt = txt.replace(/[^\d-\.,\/ ]/g, ''); 
      repvl = txt; repl = 1;
      txt = txt.replaceAll(',', '.');
      txt = txt.replaceAll(' ', ''); }
    else if (subt == 'domino') {
      txt = txt.replace(/[^0123456 ]/g, ''); 
      repvl = txt; repl = 1;
      txt = txt.replaceAll(' ', ''); 
      if (!txt.match(/^[0-6][0-6]$/)) { txt = ''; } }
    ok = subt == 'custom' ? testCheck(V['phase'], qnum, txt) : (txt != '' ? 1 : 0);
    if (ok == 1) { vl = txt.trim(); }
    if (repl == 1) { document.getElementById('qmt'+qnum).value = repvl; }
  }
  else if (tp == 'slider') {
    vl = int(dvl);
    if (vl <= 0) { vl = document.getElementById('qmt'+qnum).min; }
    if (V['qtlkey'] && vl > 9) { vl = String.fromCharCode(vl + 55); }
    ok = 1; }
  if (V['_testReCheck']) { 
    ok = testReCheck(V['phase'], qnum, vl, ok); }
  if (V['engine'] == 'qtl') {
    frmEnable('Nxt', ok, okerr);
    setVar('qm'+qnum, vl); }
  if (V['engine'] == 'qpl') {
    setVar('p'+V['phase']+'qm'+qnum, vl); 
    let qp = vl == '' ? '0' : '1';
    document.getElementById("qpLink"+qnum).className = "qp" + qp; 
    document.getElementById("qpHeader"+qnum).className = "qpHeader qp" + qp; 
    if (document.getElementById("qpHeaderMark"+qnum)) {
      document.getElementById("qpHeaderMark"+qnum).style.display = 'block'; 
      document.getElementById("qpHeaderMarked"+qnum).style.display = 'none'; }
    if (V['aall']) { qplCheckAll(); } }
}

function qmlLoadStor ()
{
   let vstor = V['loadstor'];
   let vtemp = vtest;
   vtest = vstor;
   if (int(getVar('stor_nn')) == 0) { vtest = vtemp; return errOr('stor'); }
   for (i = 1; i <= V['qtotal']; i++) {
     if (document.getElementById('stor_'+i)) {
       document.getElementById('stor_'+i).innerHTML = str(getVar('stor_'+i)); } }
   vtest = vtemp;
   if (V['_postLoadStor'] == 1) { qmlPostLoadStor(); }
}

function qtlHideOnOff (id, sw)
{
  let ov = int(getVar('hideon'));
  let ovn = sw == 0 ? ov : (ov == 1 ? 0 : 1);
  if (ovn == 1) { 
    document.getElementById('qHBS'+id).innerHTML = '&#9652;';
    ui('qHB'+id, 'block'); }
  else {
    document.getElementById('qHBS'+id).innerHTML = '&#9662;';
    ui('qHB'+id, 'none'); } 
  if (ov != ovn) { setVar('hideon', ovn); }
  return false;
}

function runCheck ()
{
  let err = '';
  let isok = 1;
  let ischeck = 0;
  if (document.getElementById('stdSexSelector')) {
    ischeck = 1;
    let val = document.getElementById("stdSexValue").innerHTML;
    if (val != 'F' && val != 'M') {
      err = (ven ? 'select gender' : 'укажите пол'); 
      isok = 0; } }
  if (document.getElementById('stdAgeSelector')) {
    ischeck = 1;
    let stdaf = int(V['agemin']);
    let stdat = int(V['agemax']);
    isageok = 1;
    let vage = getVAge();
    if (vage == '' ||
        vage < stdaf ||                                                           
        vage > stdat) {
      let aft = stdat - stdaf <= 12 ? '' : stdat == 99 ? ' (' + stdaf + '+)' : ' ('+stdaf+'-'+stdat+')';
      err = err + (err == '' ? (ven ? 'select' : 'укажите') : (ven ? ' and' : ' и'))
        + (ven ? ' age' : ' возраст') + aft; 
      isageok = 0;
      isok = 0; } 
    document.getElementById('stdAgeSelector').className = isageok ? 'finBlock fpAge' : 'finBlock fpAge finRed'; }
  if (document.getElementById('std18Selector')) {
    ischeck = 1;
    let f18 = document.getElementById('std18check').checked ? 1 : 0;
    document.getElementById('std18Selector').className = f18 ? 'finBlock fprBlank' : 'finBlock fprBlank finRed';
    if (!f18) { 
      err = err != '' ? err : 'подтвердите возраст'; 
      isok = 0; } }
  if (document.getElementById('fpBatX')) {
    ischeck = 1; }
  if (int(V['_checkbat']) == 1) {
    isok = 0;
    err = err != '' ? err : 'согласитесь или откажитесь отправлять результаты'; }
  if (ischeck == 0) { return; }
  frmEnable('Run', isok ? 1 : 0, err);
}

function runSexClick (val) 
{
  document.getElementById("stdSexValue").innerHTML = val;
  document.getElementById("stdSexT2").innerHTML = document.getElementById("stdSexCalc"+val).innerHTML;
  document.getElementById("stdSexCalc"+val).innerHTML;
  document.getElementById("stdSexCalcM").className = val == 'M' ? "stdSexCalcM" : "";
  document.getElementById("stdSexCalcF").className = val == 'F' ? "stdSexCalcF" : "";
  document.getElementById('stdSexSelector').className='finBlock fpSex'; 
  let rulM = document.getElementById('RulesM') ? true : false;
  let rulF = document.getElementById('RulesF') ? true : false;
  if (val == 'M' && rulM) {
    document.getElementById('RulesM').style.display = 'block';
    document.getElementById('Rules').style.display = 'none'; }
  if (val == 'M' && rulF) {
    document.getElementById('RulesF').style.display = 'none';
    document.getElementById('Rules').style.display = 'block'; }
  if (val == 'F' && rulF) {
    document.getElementById('RulesF').style.display = 'block';
    document.getElementById('Rules').style.display = 'none'; }
  if (val == 'F' && rulM) {
    document.getElementById('RulesM').style.display = 'none';
    document.getElementById('Rules').style.display = 'block'; }
  runCheck();
}

function runAgeClick (val, mod) 
{
  let now = "";
  if (mod == 1) {
    now = getVAge();
    if (val == 'C' || (val == 0 && now.length != 1)) {
      now = "";
    } else if (val >= "0" && val <= "9") {
      if (now.length < 2) { now = "" + now + val; } else { now = val; }
    } }
  else {
    if (V['_lastageval'] != null) {
      document.getElementById('lav'+V['_lastageval']).className = ""; }
    now = val;
    document.getElementById('lav'+val).className = "stdAgeCalcV";
    V['_lastageval'] = val; }
  document.getElementById("stdAgeValue").innerHTML = now;
  if (now == "") {
    document.getElementById("stdAgeT2").innerHTML = ""; }
  else if (mod == 3) {
    document.getElementById("stdAgeT2").innerHTML = "+"; }
  else if (now % 10 == 1 && now != 11) {
    document.getElementById("stdAgeT2").innerHTML = (ven ? '' : '&nbsp;год'); }
  else if (now % 10 > 1 && now % 10 < 5 && (now < 10 || now > 20)) {
    document.getElementById("stdAgeT2").innerHTML = (ven ? '' : '&nbsp;года'); }
  else {
    document.getElementById("stdAgeT2").innerHTML = (ven ? '' : '&nbsp;лет'); }
  runCheck();
}


function msgSend (type, val)
{
  let u = '';
  if (type == 'error') {
    u = window.location.pathname;
    if (vpage == 'qtl') { u = u+'/'+V['_qq']; }
    if (vpage == 'res') { u = u+'/'+vtest; }
    u = u+'/'+val; }
  else { u = val; }
  let xmlhttp = new XMLHttpRequest();
  xmlhttp.open('GET', '/eurl?p=psy&t='+type+'&u='+u);
  xmlhttp.send(); 
  return false;
}

function resDoFlok (flid)
{
  if (vlux == -1 || V['noflok']) { return; }
  let mm = isDesktop ? '' : 'm';
  let bid = flid == 1 ? 9223 : 13693;
  let ext = flid == 1 ? '.png' : '.gif';
  document.getElementById('resFlok').innerHTML = '<a target="_blank" onclick="msgSend(\'flok\', \'000\'+V[\'_flokid\']+V[\'code\']); return true;" href="https://share.flocktory.com/exchange/login?ssid=5605&bid='+bid+'"><div><img src="/img/flok'+flid+mm+ext+'" alt=""></div></a>';
  if (flid == 2) { document.getElementById('resFlok').style.marginTop = '30px'; }
  if (flid == 2) { document.getElementById('resFlok').style.marginBottom = '30px'; }
  V['_flokid'] = flid;
}

function resDoRate (rate)
{
  document.getElementById('resRate').style.display = 'none';
  if (V['norate'] || rate == 0) { return; }
  return msgSend('rate', vtest+':'+str(rate));
}

function fixMistake (mode)
{
  let l = window.location.pathname;
  if (mode != 2) { V['_mistake_mode'] = mode; }
  if (mode == 1 && !uinone('rmst')) {
    ui('rmst', 'none');
    return false; }
  if (mode == 3) {
    document.getElementById('rmbs').disabled = document.getElementById('chpd').checked ? false : true; 
    return true; } 
  if (mode == 1) {
    return fixMistakeMenu(); }
  if (mode == 41 || mode == 42) {
    if (V['_qq'] > 0 && document.getElementById('qtlQuestion'+V['_qq']) != null) {
      document.getElementById('qtlQuestion'+V['_qq']).style.userSelect = 'auto'; }
    let pp = "";
    if (mode == 41) {
      pp = 'Если вы заметили грамматическую ошибку, опечатку – пожалуйста, скопируйте ошибочное место в поле ниже, или напишите своими словами (например: «лишняя запятая», «опечатка в ответе») и нажмите «отправить». ';
      if (vpage == 'qtl' || vpage == 'qpl') { pp = pp + 'Тест и номер вопроса указывать не нужно.'; }
      else { pp = pp + 'Адрес страницы указывать не нужно.'; } }
    if (mode == 42) {
      pp = 'Если тест работает неправильно, можно об этом сообщить. Просьба писать развернуто: в чем именно состоит ошибка, почему вы так считаете, на какой источник опираетесь. Если вы допускаете, что ошибка или недопонимание может быть с вашей стороны (в более чем половине случаев так и есть) – лучше сообщите <a href="/support.html#contact">письмом</a> или <a href="/support.html#contact">вконтакте</a>.'; }
    document.getElementById('rmst').innerHTML = '<p>'+pp+'</p>'+'<tex'+'tarea id="rmta" placeholder="Это не форма обратной связи. Не задавайте вопросов, ответа не будет. Не указывайте персональные данные."></tex'
+'tarea><div style="display: flex; gap: 10px; align-items: center;"><button id="rmbs" onclick="fix'
+'Mistake(2);">отправить</button> '+'<div><span style="font-size: 0.9em;">нажимая кнопку «отправить» вы соглашаетесь с&nbsp;<a href="/privacy.html">политикой конфиденциальности</a>.</span></div>'; 
    ui('rmst');
    return false; }
  if (mode == 51 || mode == 52) {
    let pp = "";
    if (mode == 51) { pp = 'If you find any error – a typo, a grammar issue, a factual inaccuracy, a broken link, a technical bug, or anything that does not work as expected – feel free to report it here. We review all reports and will fix the issue where possible.'; }
    if (mode == 52) { pp = 'If you think an online version of a particular test, questionnaire, or assessment method should be added to the website, feel free to suggest it.'; }
    document.getElementById('rmst').innerHTML = '<p>'+pp+'</p>'+'<tex'+'tarea id="rmta" placeholder="Please do not submit questions, as no reply will be provided."></tex'
+'tarea><div style="display: flex; gap: 10px; align-items: center;"><button id="rmbs" onclick="fix'
+'Mistake(2);">send</button>';
    ui('rmst');
    return false; }
  if (mode == 2) {
    let t = document.getElementById('rmta').value.replace(/\n/g, " ").trim();
    if (t == "") { return false; }
    let tu = ' '+t.toUpperCase();
    let curse = getLocal('curse');
    if (curse != '' && tu.indexOf('ИЗВИНИ') >= 0) { delLocal('curse'); curse = ''; }
    if (tu.indexOf(' ПИД'+'ОР') >= 0 || tu.indexOf(' ПИД'+'АР') >= 0) { curse = 'ПИД'+'ОР'; }
    else if (tu.indexOf(' ГОВ'+'НО') >= 0 || tu.indexOf(' ГАВ'+'НО') >= 0) { curse = 'ГОВ'+'НО'; }
    else if (tu.indexOf(' ГОВ'+'НЮ') >= 0 || tu.indexOf(' ГАВ'+'НЮ') >= 0) { curse = 'ГОВ'+'НЮК'; }
    else if (tu.indexOf(' ЕБЛ'+'АН') >= 0 || tu.indexOf(' ЕБА'+'НА') >= 0 ) { curse = 'ЕБЛ'+'АН'; }
    else if (tu.indexOf('ДОЛБ'+'ОЕБ') >= 0 || tu.indexOf('ДОЛБ'+'АЕБ') >= 0 || tu.indexOf('ДАЛБ'+'АЕБ') >= 0) { curse = 'ДОЛБ'+'ОЕБ'; }
    else if (tu.indexOf('НА Х'+'УЙ') >= 0 || tu.indexOf('НАХ'+'УЙ') >= 0 || tu.indexOf('ХУ'+'ЙНЯ') >= 0 || tu.indexOf('К ХУ'+'ЯМ') >= 0 || tu.indexOf('ХУ'+'ЕСОС') >= 0  || tu.indexOf(' ЕБ'+'АЛ') >= 0 || tu.indexOf(' ЕБ'+'АТЬ') >= 0 || tu.indexOf(' УЕ'+'БО') >= 0  || tu.indexOf(' УЕ'+'БК') >= 0) { curse = 'Х'+'У'+'Й'; }
    let l = window.location.pathname;
    l = l + ':' + vtest + (V['_qq'] > 0 ? ':'+V['_qq'] : '');
    if (curse != '') { 
      setLocal('curse', curse);
      alert('ТЫ '+curse);
      msgSend('curse', '[' + l + '] ' + curse + ' / ' + t); }
    else {
      msgSend('mistake', '[' + l + '] ' + t);
      document.getElementById('rmbs').innerHTML = ven ? 'Thanks!' : 'Cпасибо!';
      if (V['_mistake_mode'] == 42 && t.length > 5) { document.getElementById('rmst').innerHTML =
'<p>Разработчик прочитает ваше сообщение, и при необходимости примет меры, <b>но ответить вам не сможет</b>.'
+' Практика показывает, что в более чем половине случаев ошибки на сайте нет, а имеет место недопонимание или '
+' недостаточное знакомство с источниками. Если тест нужен вам для дела, если важно, чтобы'
+' проблема была решена – лучше напишите <a href="/support.html#contact">письмо</a>'
+' или в группу <a href="/support.html#contact">вконтакте</a>, вам обязательно ответят.';
    } }
    document.getElementById('rmbs').disabled = true;
    return false; }
}

function fixMistakeMenu ()
{
  if (vpage == 'qtl') {
    if (vtest.substring(0,4) == 'smil' && (V['_qq'] == 14 || V['_qq'] == 33 || V['_qq'] == 48 || V['_qq'] == 63 || V['_qq'] == 66 || V['_qq'] == 69 || V['_qq'] == 121 || V['_qq'] == 123 || V['_qq'] == 133 || V['_qq'] == 151 || V['_qq'] == 168 || V['_qq'] == 182 || V['_qq'] == 184 || V['_qq'] == 197 || V['_qq'] == 200 || V['_qq'] == 205 || V['_qq'] == 266 || V['_qq'] == 275 || V['_qq'] == 293 || V['_qq'] == 334 || V['_qq'] == 349 || V['_qq'] == 350 || V['_qq'] == 462 || V['_qq'] == 464 || V['_qq'] == 474 || V['_qq'] == 542 || V['_qq'] == 551) ) {
      return fixMistakeText('smil'); } 
    if (vtest.substring(0,4) == 'smil' && V['_qq'] == 417) {
      return fixMistakeText('nepr'); } 
    if (vtest == 'garbuzov' && V['_qq'] == 36) {
      return fixMistakeText('garb'); } 
    if (vtest == 'lsi' && V['_qq'] == 9) {
      return fixMistakeText('lsiz'); } 
    if (vtest == 'epiB' && V['_qq'] == 57) {
      return fixMistakeText('sosl'); } 
    if (vtest == 'mbtix' && V['_qq'] == 18) {
      return fixMistakeText('mbtx'); } 
    if ( (vtest == 'epiAS' && V['_qq'] == 15) || (vtest == 'epq' && V['_qq'] == 30) || (vtest == 'epqR' && V['_qq'] == 33) ) {
      return fixMistakeText('eyes'); }
  }
  let sm = "";
  if (vpage == 'stu') { 
    return fixMistakeText('stdy'); }
  if (vpage == 'qtl' || vpage == 'qpl' || vpage == 'run') { 
    sm = sm + '<div><a href="#" onclick="return fixMistakeText(\'run1\');">Тест не работает, не понимаю что делать</div>'; }
  if (vpage == 'qtl' || vpage == 'qpl') { 
    sm = sm +'<div><a href="#" onclick="return fixMistakeText(\'run3\');">Не нравится, не понятна формулировка вопроса</div>'
+ '<div><a href="#" onclick="return fixMistakeText(\'run2\');">Нет подходящего варианта ответа</div>'; }
  if (vpage == 'ind' || vpage == 'res') { 
    sm = sm + '<div><a href="#" onclick="return fixMistake(42);">Тест работает неправильно</div>'; }
  if (vpage == 'run' && vtest == 'rokeach') {
    sm = sm + '<div><a href="#" onclick="return fixMistakeText(\'roke\');">Не хватает номеров, нет номера 19</div>'; }
  if (vpage == 'bla') { 
    sm = sm + '<div><a href="#" onclick="return fixMistakeText(\'blnk\');">Неправильно указаны баллы за ответы</div>'; }
  if (V['_rrr']) {  
    sm = sm + '<div><a href="#" onclick="return fixMistakeText(\'unav\');">Тест недоступен</div>'; }
  let xad = 0;
  if (vpage == 'res' && document.getElementById('abc')) { 
    if (document.getElementById('abc').innerHTML.startsWith('Adblock')) {
      sm = sm + '<div><a href="#" onclick="return fixMistakeText('+"'nres'"+');">Тест не показывает результаты</a></div>';
      xad = 1; } }
  if (sm != "" && xad ==0) { sm = '<div><a href="#" onclick="return fixMistake(41);">Грамматическая ошибка, опечатка в тексте</a></div>' + sm; }
  if (ven) { 
    sm = '<div><a href="#" onclick="return fixMistake(51);">Report an error</a></div><div><a href="#" onclick="return fixMistake(52);">Make a suggestion</a></div>'; }
  if (sm != "") { document.getElementById('rmst').innerHTML = '<div class="tl x2">'+sm+'</div>'; ui('rmst'); return false; }
  return fixMistake(41);
}

function fixMistakeText (fid)
{
  let st = '';
  if (fid == 'smil') { st = 'Здесь нет ошибки. Перед тестом была инструкция, вы ее не прочитали. Прочитайте, там всё написано.'; }
  if (fid == 'lsiz') { st = 'Здесь нет ошибки. Google/Яндекс: "значение слова задаваться".'; }
  if (fid == 'sosl') { st = 'Здесь нет ошибки. Google/Яндекс: "значение фразы сосёт под ложечкой".'; }
  if (fid == 'nepr') { st = 'Здесь нет ошибки. Google/Яндекс: "значение фразы не премину".'; }
  if (fid == 'eyes') { st = 'Здесь нет ошибки. Если вы не понимаете смысл вопроса, обратитесь в своему учителю.'; }
  if (fid == 'mbtx') { st = 'Здесь нет ошибки. Так в книге. Формулировки грамматически корректны.'; }
  if (fid == 'blnk') { st = 'Номера ответов – это просто номера колонок с ответами. Это НЕ баллы для подсчета показателей. Об этом написано прямо под бланком.'; }
  if (fid == 'garb') { st = 'Здесь нет цифры 2 и цифры 6. Автор составил тест без этих цифр. Выбирайте из предложенных вариантов.'; }
  if (fid == 'nres') { st = 'Скорее всего, ваш блокировщик рекламы посчитал результаты теста рекламой и заблокировал. Возможно, виновато какое-то иное расширение браузера.'; }
  if (fid == 'run1') { st = 'Внимательно прочитайте инструкцию перед тестом. Если инструкция не помогла, <a target="_blank" href="/support.html">читайте здесь</a>.'; }
  if (fid == 'run2') { st = 'Если вы проходите тест по направлению психолога (врача, учителя) – обратитесь за разъяснениями к нему.</p> <p>Если проходите самостоятельно, то соберитесь с силами и выберите что-нибудь. Автор составил тест только с такими ответами, других нет. Разработчик сайта автором теста не является и авторские формулировки <a target="_blank" href="/support.html#fml">менять не будет</a>.'; } 
  if (fid == 'run3') { st = 'Если вы проходите тест по направлению психолога (врача, учителя) – обратитесь за разъяснениями к нему.</p> <p>Если проходите самостоятельно, то соберитесь с силами и как-нибудь ответьте. Автор теста сформулировал вопрос именно так. Разработчик сайта автором теста не является и авторские формулировки <a target="_blank" href="/support.html#fml">менять не будет</a>.'; } 
  if (fid == 'stdy') { st = 'Если вы нашли ошибку на этой странице, пожалуйста, обращайтесь напрямую к специалисту, проводящему исследование.'; }
  if (fid == 'unav') { st = 'Да, тест недоступен. Это не ошибка.'; }
  if (fid == 'roke') { st = 'Ценностей в каждом списке – по 18. И рангов – 18. Вы какой-то номер пропустили. Будьте внимательнее.'; }
  if (st != "") { document.getElementById('rmst').innerHTML = '<p>'+st+'</p>'; ui('rmst'); }
  return false;
}

function blankFill (qq)
{
  let qa = qq;
  if (!qa) { qa = window.location.search; qa = qa.replace(/^\?/, ''); }
  if (!qa) { return; }
  let qml = str(V['bqml']);
  let blc = V['blch'] == 1 ? 1 : 0;
  let blf = V['customBlankVal'] == 1 ? 1 : 0;
  let wmax = qa.substring(0,1);
  if (wmax >= 'A') { wmax = wmax.charCodeAt(0)-54; }
  qa = encodec(qa.substring(1), 64, int(wmax));
  if (qa.length != (int(V['btotal']) + 2)) { return; }
  let sex = qa.substring(1,2);
  if (str(V['bqml']) != '') {
    for (let i = 1; i <= qa.length-2; i++) {
      let s = qa.substring(i+1, i+2);
      if (s.charCodeAt(0) < 48 || s.charCodeAt(0) >= 65) { s = encodec(s, 64, 10); }
      let a = (int(V['blzk']) == 1 ? 0 : 1) + parseInt(s);
      if (a != 0) {
        document.getElementById('q'+i+'a1').innerHTML = blc == 1 ? '&check;' : (blf ? customBlankVal(a) : a);
        if (blc == 1 && document.getElementById('qb'+i+'a1')) {
          document.getElementById('qb'+i+'a1').className = document.getElementById('qb'+i+'a1').className + " bl2ASel"; } }
    }
  } else {
    for (let i = 1; i <= qa.length-2; i++) {
      let s = qa.substring(i+1, i+2);
      if (s.charCodeAt(0) < 48 || s.charCodeAt(0) >= 65) { s = encodec(s, 64, 10); }
      let a = 1 + parseInt(s);
      document.getElementById('q'+i+'a'+a).innerHTML = blc == 1 ? '&check;' : (blf ? customBlankVal(a) : a);
      if (document.getElementById('qb'+i+'a'+a)) {
        document.getElementById('qb'+i+'a'+a).className = document.getElementById('qb'+i+'a'+a).className + " bl2ASel"; } 
    }
  }
  if (document.getElementById('BLSX')) { 
    document.getElementById('BLSX').style.display = 'none'; } 
}

function getAvgTime (at, eng)
{
  if (int(at) == 0) { return ''; }
  if (at < 55) { return eng ? 'less 1 min' : '1 минута'; }
  at = int(at/60) + (at%60 > 30 ? 1 : 0);
  if (eng) { if (at == 1) { return '1 min'; } else { return at+' min'; } }
  let ats = str(at);
  if (ats.endsWith('1') && at != 11) { return ats+' минута'; }
  if ((ats.endsWith('2') || ats.endsWith('3') || ats.endsWith('4')) && at != 12 && at != 13 && at != 14) { return ats+' минуты'; }
  return ats+' минут'; 
}

function getQstNum (qn, eng)
{
  if (int(qn) == 0) { return ''; }
  if (eng) { if (qn == 1) { return '1 item'; } else { return qn+' items'; } }
  let qns = str(qn);
  if (qns.endsWith('1') && !(qns.endsWith('11'))) { return qns+' вопрос'; }
  if ( (qns.endsWith('2') || qns.endsWith('3') || qns.endsWith('4'))
   && !(qns.endsWith('12') || qns.endsWith('13') || qns.endsWith('14')) ) { return qns+' вопроса'; }
  return qns+' вопросов'; 
}

function HTB (path, title, at, qn, flags, spl, set)
{
   if (V['_search'] == 1) { if (V['_search_last'] == title) { return ""; } else { V['_search_last'] = title; } }
   let eng = flags.includes('E') ? 1 : 0;
   let rrr = flags.includes('X') && !V['_navru'] ? 1 : 0;
   if (rrr) { V['_rrr'] = 1; }
   let run = flags.includes('R') ? 1 : 0;
   let off = flags.includes('O') ? 1 : 0;
   if (off || flags.includes('U')) { rrr = 1; }
   if (int(at) != 0) { at = getAvgTime(at, eng); } else { at = ''; }
   if (!flags.includes('Q')) { qn = int(qn) > 0 ? getQstNum(qn, eng) : ''; }
   if (qn == 'L4') { qn = '<span class="lf1">&#9646;</span><span class="lf2">&#9646;</span><span class="lf3">&#9646;</span><span class="lf4">&#9646;</span>'; }
   let sample = rrr ? '' : (spl ? '<a href="/result?v='+spl+'&pp=1">'+(eng ? 'sample' : 'пример')+'</a>' : '');
   if (!rrr && flags.includes('B')) { 
     sample = '<a href="/'+path+'-bl.html">'+(eng ? 'form' : 'бланк')+'</a>'+(sample ? ' | '+sample : ''); }
   let url = '/'+path+(run ? '-run' : '')+'.html';
   if (!run || (!rrr && !off)) { title = '<a href="'+url+'">'+title+'</a>'; }
   if (off && run) { off = 0; rrr = 1; }
   let button = 
    off ? (eng ? 'INFO' : 'ОПИСАНИЕ') :
    rrr ? (eng ? 'UNAVAILABLE' : 'НЕДОСТУПЕН') : 
    run ? (eng ? 'BEGIN' : 'ПРОЙТИ') : 
          (eng ? 'ONLINE' : 'ОНЛАЙН');
   let lsample = (off || rrr) ? button.toLowerCase() : sample;
   if (off) { button = '<div class="tbButton tbNoButton tbNoInfo">'+button+'</div>'; }
   else if (rrr) { button = '<div class="tbButton tbNoButton tbNoForbid">'+button+'</div>'; }
   else { button = '<a href="'+url+'" class="tbButton'+(!run ? ' tbButtonHide' : '')+'">'+button+'</a>'; }
   if (set == undefined) { set = ''; } else if (set != '') { set = '<a href="/'+set+'</a>'; }
   let block = '<div class="tbBlofx"><div class="tbLeft"><div>'+qn+'</div><div>'+at+'</div><div class="tbSampleL">'+lsample+'</div></div>' +
'<div class="tbMain"><div class="tbTitle">'+title+'</div><div class="tbSub"><div class="tbIndex">'+set+'</div>' +
'<div class="tbSample">'+sample+'</div></div></div>'+button+'</div>';
  if (flags.includes('I')) { 
    let name = path.substring(path.indexOf('/')+1);
    if (document.getElementById('ht'+name)) {
      let ht = document.getElementById('ht'+name).innerHTML;
      let htx = ht.indexOf('<div class="tauad">');
      if (htx > 0) { ht = ht.substring(htx); } else { ht = ''; }
      document.getElementById('ht'+name).innerHTML = block+ht; return 0; } }
  return '<div class="tbBlock'+(run ? '' : ' tbList')+'">'+block+'</div>'; 
}

function calconoff () { return hideonoff('calc'); }
function hideonoff (s)
{
  if (document.getElementById(s).style.display == 'none') {
    document.getElementById(s).style.display = 'block';
    document.getElementById(s+'tr').innerHTML = '&#9652;';
    if (document.getElementById(s+'style')) {
      document.getElementById(s+'style').remove(); } }
  else {
    document.getElementById(s).style.display = 'none';
    document.getElementById(s+'tr').innerHTML = '&#9662;'; }
  return false;
}

function hideon (s)
{
  if (document.getElementById(s).style.display == 'none') {
    document.getElementById(s).style.display = 'block';
    document.getElementById(s+'tr').innerHTML = '&#9652;'; }
  return true;
}

function frmEnable (form, enable, err) {
  if (!document.getElementById('std'+form)) { return; } 
  document.getElementById('std'+form+'Button').disabled = enable == 1 ? false : true;
  let final = false;
  if (form == 'Res') { final = true; }
  if (final && V['engine'] == 'qpl' && int(V['phase']) != int(V['qphase'])) { final = false; }
  if (final) {
    if (enable) { runFinal(); } 
    ui('stdFinal', enable ? 'block' : 'none'); }
  if (err != undefined) {
    document.getElementById('std'+form+'Err').innerHTML = enable == 0 && err != "" ? err : '&nbsp;'; } }

function frmValue (form, val) {
  if (document.getElementById('std'+form)) { 
    document.getElementById('std'+form+'Button').value = val; } }

function endec (source, base) { return encodec(source, base, 64); }
function encodec (source, base, baseto)
{
  var CHARS = '0123456789-_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';
  var len = source.length;
  var num = new Array(); 
  for (var i = 0; i < len; i++) { num[i] = CHARS.indexOf(source.charAt(i)); }
  var result = '';
  var newlen = 1; 
  var divide = 0;
  while (newlen != 0) { 
    divide = 0; 
    newlen = 0;
    for (var i = 0; i < len; i++) {
      divide = divide * base + num[i];
      if (divide >= baseto) { 
        num[newlen++] = Math.floor(divide/baseto);
        divide = divide % baseto; 
      } else {
        if (newlen > 0) { num[newlen++] = 0; } } }
    len = newlen; 
    result = CHARS.charAt(divide) + result; } 
  return result; 
}

var backListener = function (e) { (e || window.event).returnValue = true; return true; };

function backBlock (onoff)
{
  if (onoff == 1) {
    window.addEventListener("beforeunload", backListener, false); }
  else {
    window.removeEventListener('beforeunload', backListener, false); }
}

function bySL (hid, aid, lid)
{
  if (aact != 0) { 
    document.getElementById('au'+aact).className = 'byAD';
    document.getElementById('au'+aact).style.height = bybase + 'px'; }
  if (aact != 0 && aact == aid) {
    document.getElementById('byb'+lid).style.display = 'none';
    aact = 0;
    return false; }
  if (lact != 0 && lid != lact) {
    document.getElementById('byb'+lact).style.display = 'none'; }
  lact = lid;
  aact = aid;
  bybase = document.getElementById('au'+aid).offsetHeight;
  let sd = '';
  hid.split(' ').forEach( (s) => {
    let nm = sdiv[s];
    let ss = nm.split('|');
    let md = ss[2] == 'F' ? '<div class="iFM iFMF">&female;</div>' :
             ss[2] == 'M' ? '<div class="iFM iFMM">&male;</div>' :
             ss[2] == 'P' ? '<div class="iFM iFMF">&#9825;</div>' : 
             ss[2] == 'S' ? '<div class="iFM">»</div>' : 
             ss[2] == 'Y' ? '<div class="iFM">&frac12;</div>' : 
             ss[2] == 'D' ? '<div class="iFM iPencil"></div>' : '';
    let ac = ss[2] == 'U' ? 'class="byAG" ' : '';
    if (byrusd && byRUSD[s]) { ss[1] = '<b>'+ss[1]+'</b>'; }
    sd = sd + '<div><a '+ac+'href="/'+ss[0]+'/'+s+'.html">'+ss[1]+'</a>'+md+'</div>'; 
  } );
  document.getElementById('byb'+lid).innerHTML = sd; 
  document.getElementById('byb'+lid).style.display = 'flex';
  document.getElementById('byb'+lid).style.width = (document.getElementById('byl'+lid).offsetWidth - 10) + 'px';
  document.getElementById('byb'+lid).style.top = (bybase + document.getElementById('au'+aid).offsetTop) + 'px';
  document.getElementById('au'+aid).className = 'byAD bySel';
  document.getElementById('au'+aid).style.height = (bybase + 20 + document.getElementById('byb'+lid).offsetHeight) + 'px';
/*  document.getElementById('au'+aid).scrollIntoView({behavior: "smooth"}); */
/* ss[2] == 'U' ? '<div class="iFM">&#128711;</div>' : */
  return false;
}

function byAZY (mode)
{
  if (mode == 'AZ') {
    document.getElementById('byfAZ').className = 'bySel';
    document.getElementById('byfAY').className = '';
    document.getElementById('byAZ').style.display = 'block';
    document.getElementById('byAY').style.display = 'none';
  } else {
    document.getElementById('byfAY').className = 'bySel';
    document.getElementById('byfAZ').className = '';
    document.getElementById('byAY').style.display = 'block';
    document.getElementById('byAZ').style.display = 'none';
  }
  return false;
}

function byAZF (mode)
{
  if (aact != 0) { bySL(0, aact, lact); }
  let v = document.getElementById('byfilter').value.toUpperCase().replaceAll('Ё', 'Е').replace(/[^A-ZА-Я]/g, "").trim();
  if (v == bylast) { return false; }
  bylast = v;
  let re = new RegExp((mode == 1 && v.length > 2 ? '' : '^') + v);
  let showl = v == '' ? 1 : 0;
  for (let j = 1; j <= byL; j++) {
    document.getElementById('byp'+j).style.display = showl ? 'flex' : 'none';
  }
  for (let i = 1; i <= byA; i++) {
    let adiv = document.getElementById('au'+i);
    let ahref = adiv.firstChild;
    let dtag = ahref.dataset.tag;
    let dname = ahref.innerHTML + (dtag ? ' '+dtag : '');
    let show = showl ? 1 : (dname.toUpperCase().replaceAll('Ё', 'Е').match(re) ? 1 : 0);
    adiv.style.display = show == 1 ? 'block' : 'none'; 
    if (show) { adiv.parentElement.parentElement.style.display = 'flex'; }
  } 
  if (mode != 1 && !showl) {
    if (v.match(/^[A-Z]/)) { byAZY('AZ'); } else { byAZY('AY'); } }
}

function hdFind ()
{
  let v = document.getElementById('hdfi').value.trim();
  if (v == "") { return false; }
  document.location = "/search" + (ven ? "en" : '') + ".html?" + encodeURI(v);
  return false;
}

function fixFind ()
{
  ui('hdwl', 'none');
  ui('hdfd');
  document.getElementById('hdfi').focus();
}

function hdMenu (mode,level)
{
  if (document.getElementById('HDP').innerHTML == '') { initMenu(); }
  if (mode == 1 && level == 0) { ui('HDP'); ui('BGM1'); }
  if (mode == 0 && level == 0) {
    if (str(V['_menu_shown']) != '') {
      ui(V['_menu_shown'], 'none'); 
      V['_menu_shown'] = ''; }
    ui('HDP', 'none'); ui('BGM1', 'none'); }
  return false;
}

function hdSubMenu (subm) 
{
  let lastm = str(V['_menu_shown']);
  if (str(V['_menu_shown']) != '') {
    ui(V['_menu_shown'], 'none'); 
    V['_menu_shown'] = ''; }
  if (uinone(subm) && lastm != subm) {
    ui(subm);
    V['_menu_shown'] = subm }
  else {
    ui(subm, 'none'); } 
}

function initMenu ()
{
  V['_MENU_MAIN'] = ven ? '/en.html|Main|/guide/guide-en.html|Guide|/tagsen.html|Tags|/authorsen.html|Authors|/newsen.html|New|/searchen.html|Search|-|-|/guide/pop-self-discovery-en.html|Self-Discovery|-|-|/abouten.html|About' :
(vuser ? (getLocal('uKind') == 'R' ? '>USER|рабочий кабинет|-|-|' : '>USER|личный кабинет|-|-|') : '') +
'>FUN|тесты для всех|>PRO|для специалистов|>TYP|направления|/authors.html|тесты по авторам|' +
'/top.html|топ-50 тестов|/newtop.html|новые тесты|-|-|/articles.html|статьи|>SITE|о сайте';
  if (!ven) {
    V['_MENU_PRO'] = '/tags.html|тематический каталог|/authors.html|указатель авторов|/new2026.html|тесты последних лет|-|-|' +
'/tags/clinical.html|клинические методики|/tags/cbt.html|когнитивная терапия|/tags/family.html|семейная психология|/tags/organizational.html|организационная|/tags/proforientation.html|профориентация|-|-|/rabcab.html|рабочий кабинет';
    V['_MENU_FUN'] = '/map.html|популярные тесты|/funset.html|серии тестов|/random.html|случайный тест|/tags/funmf.html|отношения и секс|-|-|' +
'/tags/projective.html|проективные тесты|/tags/typology.html|типы личности|/tags/cognitivestyle.html|когнитивные стили|/tags/intellect.html|тесты интеллекта|/tags/proforientation.html|профориентация|/tags/business.html|деловые тесты';
    V['_MENU_TYP'] = '/tags/positive.html|позитивная психология|/tags/existenz.html|экзистенциальная|/tags/selfdetermination.html|самодетерминация|/tags/ta.html|транзактный анализ'+
'|-|-|/tags/ethnopsychology.html|этнопсихология|/tags/cyberpsy.html|киберпсихология|/tags/sportpsychology.html|спортивная психология'; 
    V['_MENU_SITE'] = '/about.html|общая информация|/agreement.html|условия использования|/privacy.html|политика пдн|/support.html|поддержка и контакты|/addtest.html|предложить тест|' +
'-|-|/book/index.html|литература|/todo.html|фронт работ';
    if (vuser) { V['_MENU_USER'] = (getLocal('uKind') == 'R' ? 
'/cab.html|мои исследования|/cabdata.html|данные респондентов|/cabank.html|мои анкеты|/caborg.html|мои профили' : '/my.html|мои результаты') +
'|/favorites.html|избранные тесты|-|-|/account.html|настройки|EXIT|выход'; } }
  document.getElementById('HDP').innerHTML = uiMenu();
  return false;
}

function uiMenu (id)
{
  let html = '';
  let ar = V['_MENU_MAIN'].split('|');
  for (i = 0; i < ar.length; i = i + 2) {
    if (ar[i] == '-') { html = html + '<div class="hdLine"></div>'; }
    else if (ar[i].startsWith('>')) { 
      let subm = ar[i].substring(1);
      html = html + '<div class="hdSub"><a href="#" onclick="return hdSubMenu(\'HD'+subm+'\');">'+ar[i+1]+'</a>'
+ '<span>&#9664;</span>	<div class="hdPopup" id="HD'+subm+'">';
      let sr = V['_MENU_'+subm].split('|');
      for (k = 0; k < sr.length; k = k + 2) {
        if (sr[k] == '-') { html = html + '<div class="hdLine"></div>'; }
        else if (sr[k] == 'EXIT') { html = html + '<a href="#" onclick="userLogMeOut();">выход</a>'; }
        else { html = html + '<a href="'+sr[k]+'">'+sr[k+1]+'</a>'; } }
      html = html + '</div></div>'; }
    else { html = html + '<a href="'+ar[i]+'">'+ar[i+1]+'</a>'; } }
  return html;
}

function varFixWidth (tvar) 
{
  let minw = 1000;
  let maxw = 0;
  var chvar = document.getElementById(tvar).children;
  for (let i = 0; i < chvar.length; i++) {
    var ch = chvar[i];
    if (ch.offsetWidth < minw) { minw = ch.offsetWidth; }
    if (ch.offsetWidth > maxw) { maxw = ch.offsetWidth; } }
  if (minw == maxw) { return; }
  for (let i = 0; i < chvar.length; i++) {
   chvar[i].style.minWidth = maxw + 'px'; }
}

function varSelect (varvar, varval) 
{
  let oldval = str(V[varvar]);
  if (oldval != "" && oldval != varval) {
    document.getElementById('var_'+varvar+oldval).className = ''; }
  document.getElementById('var_'+varvar+varval).className = 'testVS';
  V[varvar] = varval;
  V['_setvar'] = varvar;
  return false;
}

function checkLogin (l)
{
  let ll = l.replace(/[A-Za-z0-9\!\@\$\%\&\*\_\-\+\=\:\.]/g, '');
  return ll == "" ? true : false; 
}

function checkPass (l) 
{
  let ll = l.replace(/[A-Za-z0-9\~\`\!\@\#\$\%\^\&\*\(\)\_\-\+\=\{\[\}\]\|\\\:\;\"\'\<\,\>\.\?\/]/g, '');
  return ll == "" ? true : false; 
}

function xhrReq (req, errd, callback, errc)
{
  if (int(V['_req_is_on']) == 1) { return false; }
  V['_req_is_on'] = 1;
  let xhr = new XMLHttpRequest();
  xhr.open('POST', '/user', true);
  let post = '';
  if (typeof req === 'string') {
    post = req; }
  else {
    for (var key in req) { 
      if (req.hasOwnProperty(key)) { 
      post = post + (post == '' ? '' : '&') + key + '=' + encodeURIComponent(req[key]); } } }
  xhr.send(post);
  xhr.onload = function() {
    let err = 0;
    let resp = '';
    if (xhr.status != 200) { err = 1400; }
    if (err == 0) {
      resp = xhr.responseText.trim(); 
      if (!resp.startsWith('0|')) { err = errServer(resp) != '' ? resp : 1400; } } 
    V['_req_is_on'] = 0;
    if (err > 0) { 
      if (err == 1424) { userLogout(1); }
      else if (errd && document.getElementById(errd)) { document.getElementById(errd).innerHTML = errServer(err); } 
      else if (errd != 'none') { errBox(errServer(err)); } 
      if (errc) { errc(err); } }
    else { 
      if (errd && document.getElementById(errd)) { 
        document.getElementById(errd).innerHTML = '&nbsp;'; }
      else if (errd != 'none' && !uinone('errBox')) { ui('errBox', 'none'); }
      if (callback) { 
/*        if (document.getElementById('nodebug')) { document.getElementById('nodebug').innerHTML = resp; } */
        callback(resp); } } } 
}

function userAnon()
{
  let uid = int(getLocal('uAnon'));
  if (uid > 0) { return uid; }
  let xhr = new XMLHttpRequest();
  xhr.open('POST', '/user', false);
  xhr.send('a=anon');
  if (xhr.status != 200) { return 0; }
  uid = int(xhr.responseText.trim());
  setLocal('uAnon', uid);
  return uid;
}

function userLogout(r)
{
  delLocal('uTkn');
  delLocal('uKind');
  delLocal('uSex');
  delLocal('uAge');
  delLocal('uFlag'); 
  delLocal('uPing');
  userIcon();
  if (r == 1) { document.location = '/logon.html'; }
  return false;
}

function userPing(p)
{
  let resp = p;
  if (str(resp) == '') {
    let xhr = new XMLHttpRequest();
    xhr.open('POST', '/user', false);
    xhr.send('a=ping&tkn='+getLocal('uTkn'));
    if (xhr.status != 200) { return false; }
    let rr = xhr.responseText.trim();
    if (!rr.startsWith('0|')) { userLogout(1); return false; } 
    userPing(rr);
    return true; }
  let a = resp.split(/\|/);
  if (a[0] != '0' || (a[2] != 'U' && a[2] != 'R') || a[1] == '') { userLogout(1); }
  setLocal('uTkn', a[1]);
  setLocal('uKind', a[2]);
  if (a[3] == 'F' || a[3] == 'M') { setLocal('uSex', a[3]); }
  let age = int(a[4]);
  if (age >= 16 && age < 99) { setLocal('uAge', age); }
  setLocal('uPing', Math.floor(new Date().getTime() / 1000));
  userIcon();
  return true;
}

function userIcon()
{
  if (!document.getElementById('HLG1')) { return; }
  document.getElementById('HLG1').style.display = vuser ? 'block' : 'none';
  document.getElementById('HLG0').style.display = vuser ? 'none' : 'block';
  if (vuser) { 
    let kind = getLocal('uKind');
    if (kind == 'U') { document.getElementById('HLG1').href = '/my.html'; }
    if (kind == 'R') { document.getElementById('HLG1').href = '/cab.html'; } }
}

V['urez'] = int(getLocal('uREZ'));
V['upag'] = int(getLocal('uPAG'));
setLocal('uPAG', V['upag'] > 999999 ? 1 : V['upag'] + 1);
let isDesktop = window.matchMedia('(min-width: 1260px)').matches ? true : false;
let isFloor = window.matchMedia('(max-device-width: 720px)').matches ? true : false;
if (int(getLocal('diza')) < (new Date().getTime())) { delLocal('diza'); } else { vlux = -1; }

var ND = {
'camp:prop':'pp',
'camp:res':'rwt rpp rmp',
'camp:wide':'wu pp',
'partner:psypsy:inn':'780443542926',
'partner:psypsy:inpp':'/eurl?p=napp5&erid=2Vtzqujq7PY&u=/result',
'partner:psypsy:name':'ИП Шумилов А.С.',
'partner:psypsy:ppp':'70',
'partner:wikium:inn':'7725805647',
'partner:wikium:name':'ООО «Викиум»',
'partner:prosto:inn':'366208819519',
'partner:prosto:name':'ИП Барсуков А.А.',
'pp:erid':'2Vtzqujq7PY',
'pp:nmax':'6',
'pp:partner':'psypsy',
'pp:prefix':'pp',
'pp:style':'background-color: #00c2ff; color: #FFF; text-shadow: 0 0 0;',
'pp:t0':'Тест – это только начало, а дальше PsyPsy.online! Получите поддержку психолога со скидкой 50% на первую неделю по промокоду PSYTESTS!',
'pp:t1':'Не останавливайтесь на тесте! Узнайте, как укрепить свою психику с профессиональными психологами сервиса PsyPsy.online. Промокод PSYTESTS – скидка 50% на первую неделю!',
'pp:t2':'Ищете удобный формат помощи? Психологи PsyPsy.online предлагают чат + 30-минутную сессию в неделю. Можно заменить на 60-минутную сессию. Скидка 50% по промокоду PSYTESTS!',
'pp:t3':'Есть ответы, но где решение? Психологи PsyPsy.online помогут найти его – скидка 50% на первую неделю по промокоду PSYTESTS.',
'pp:t4':'Нашли проблему? Пора её решить. Психологи PsyPsy.online помогут вам: скидка 50% на первую неделю работы по промокоду PSYTESTS!',
'pp:t5':'Пройдите первую неделю с психологом PsyPsy.online со скидкой 50%! Введите промокод PSYTESTS и выберите удобный формат — чат + 30-минутная сессия или классическая 60-минутная сессия.',
'pp:t6':'Хотите разобраться в себе после теста? Психологи PsyPsy.online помогут – скидка 50% на первую неделю с промокодом PSYTESTS.',
'pp:type':'wide',
'rpp:erid':'2Vtzqujq7PY',
'rpp:nmax':'96',
'rpp:nmin':'90',
'rpp:partner':'psypsy',
'rpp:prefix':'pp',
'rpp:stylespan':'color:#0094FF; text-shadow: 0 0 0;',
'rpp:t90':'Тест – это только начало, а дальше <span>PsyPsy.online</span>! Получите поддержку психолога со скидкой <b>50%</b> на первую неделю по промокоду <b>PSYTESTS</b>!',
'rpp:t91':'Не останавливайтесь на тесте! Узнайте, как укрепить свою психику с профессиональными психологами сервиса <span>PsyPsy.online</span>. Промокод <b>PSYTESTS</b> – скидка <b>50%</b> на первую неделю!',
'rpp:t92':'Ищете удобный формат помощи? Психологи <span>PsyPsy.online</span> предлагают чат + 30-минутную сессию в неделю. Можно заменить на 60-минутную сессию. Скидка <b>50%</b> по промокоду <b>PSYTESTS</b>!',
'rpp:t93':'Есть ответы, но где решение? Психологи <span>PsyPsy.online</span> помогут найти его – скидка <b>50%</b> на первую неделю по промокоду <b>PSYTESTS</b>.',
'rpp:t94':'Нашли проблему? Пора её решить. Психологи <span>PsyPsy.online</span> помогут вам: скидка <b>50%</b> на первую неделю работы по промокоду <b>PSYTESTS</b>!',
'rpp:t95':'Пройдите первую неделю с психологом <span>PsyPsy.online</span> со скидкой <b>50%</b>! Введите промокод <b>PSYTESTS</b> и выберите удобный формат — чат + 30-минутная сессия или классическая 60-минутная сессия.',
'rpp:t96':'Хотите разобраться в себе после теста? Психологи <span>PsyPsy.online</span> помогут – скидка <b>50%</b> на первую неделю с промокодом <b>PSYTESTS</b>.',
'rpp:type':'result',
'_rpp:type':'wide',
'_rpp:style':'background-color: #00c2ff; color: #FFF; text-shadow: 0 0 0;',
'rmp:partner':'prosto',
'rmp:prefix':'mp',
'rmp:erid':'2VtzquipHAf',
'rmp:nmax':'94',
'rmp:nmin':'90',
'rmp:t90':'250+ медитаций под любое состояние и настроение, чтобы вернуться к себе и почувствовать себя лучше. Попробуйте <span>Prosto Meditation</span> — 14 дней за 1&#8381;.',
'rmp:t91':'Попробуйте 250+ медитаций и практик для сна, расслабления и концентрации в приложении <span>Prosto</span>. 14 дней за 1&#8381;',
'rmp:t92':'Доступ за 1&#8381; к 250+ практикам, которые помогают почувствовать себя лучше. Просто попробуйте и послушайте, как внутри.',
'rmp:t93':'Когда сложно разобраться в себе — включите медитацию в <span>Prosto</span>, чтобы понять себя и стало легче. Попробуйте 14 дней за 1&#8381;',
'rmp:t94':'Успокойтесь и выдохните в <span>Prosto Meditation</span>, чтобы услышать, что с вами на самом деле. Начните с медитации — 14 дней бесплатно.',
'rmp:stylespan':'text-shadow: 0 0 0;',
'rwt:erid':'25H8d7vbP8SRTvG4sCP46A',
'rwt:nmax':'99',
'rwt:nmin':'99',
'rwt:partner':'wikium',
'rwt:prefix':'wt',
'rwt:stylespan':'color:#0094FF; text-shadow: 0 0 0; text-transform: uppercase;',
'rwt:t99':'С любым эмоциональным состоянием способен справиться наш собственный мозг. Держать его в тонусе можно с помощью регулярных тренировок на <span>онлайн-тренажерах</span>. Используйте промокод <b>PSYTESTS</b>.',
'rwt:type':'result',
'wide0':'wu',
'wide1':'pp',
'wide2':'wt',
'wide:nmax':'2',
'wt:erid':'25H8d7vbP8SRTvG4sCP46A',
'wt:partner':'wikium',
'wt:prefix':'wt',
'wt:style':'background-image: linear-gradient(89deg, #856fc290, #ca74df90, #856fc290); color: #630063;',
'wt:stylespan':'color: #309; text-transform: uppercase; font-weight: bold;',
'wt:t0':'С любым эмоциональным состоянием способен справиться наш собственный мозг. Держать его в тонусе можно с помощью регулярных тренировок на <span>онлайн-тренажерах</span>.',
'wt:type':'wide',
'wu:erid':'25H8d7vbP8SRTvG4sCP46A',
'wu:nmax':'4',
'wu:partner':'wikium',
'wu:prefix':'wu',
'wu:style':'background-image: linear-gradient(89deg, #856fc2, #ca74df, #856fc2); color: #FFF;',
'wu:stylespan':'color: #FFFF00; text-transform: uppercase; padding-left: 2px;',
'wu:t0':'Курс <span>Эмоциональный интеллект</span>. Научитесь управлять своими эмоциями, эффективнее выстраивать коммуникацию в личных отношениях и на работе.',
'wu:t1':'Курс <span>Развитие внимания</span>. Научитесь управлять своим вниманием, концентрироваться на задачах и эффективно получать информацию.',
'wu:t2':'Курс <span>Идеальный русский</span>. Пишите без ошибок, учитесь красиво излагать свои мысли.',
'wu:t3':'Курс <span>Мышление Шерлока</span>. Узнайте всё о логическом мышлении, научитесь грамотно выстраивать аргументы и принимать верные решения.',
'wu:t4':'Курс <span>Скорочтение</span>. Научитесь читать и понимать любой текст в 3-4 раза быстрее, быстро подготовиться к экзамену, развить гибкость ума.',
'wu:type':'wide',
};

function nac (camp, ad, div) 
{
  if (vlux == -1) { return ''; }

  if (camp == 'fly') {
    let div = 'NacFly1';
    if (!document.getElementById(div)) {
      div = 'NacFly'; 
      if (!document.getElementById(div)) { return 0; } }
    let dm = window.matchMedia('(min-width: 640px)').matches ? 'd' : 'm';
    let url = dm == 'd' ? 'https://freudly.ai/?erid=4Pzz6yKjflu&utm_source=psytests&utm_medium=banner&utm_campaign=promo-1000-90' : 'https://freudly.ai/?erid=2VtzqvwUoRm&utm_source=psytests&utm_medium=banner&utm_campaign=promo-400-250';
    document.getElementById(div).innerHTML = '<div style="text-align: center; margin-top: 20px; margin-bottom: 20px;"><a href="'+url+'"><img src="/img/fly'+dm+'.png" alt="" style="max-width: 100%;"></a></div>';
    return 0; }

  if (camp == 'nad') {
    let div = 'NacNad1';
    if (!document.getElementById(div)) {
      div = 'NacNad'; 
      if (!document.getElementById(div)) { return 0; } }
    let dm = window.matchMedia('(min-width: 640px)').matches ? 'd' : 'm';
    document.getElementById(div).innerHTML = '<div style="text-align: center; margin-top: 20px; margin-bottom: 20px;"><a target="_blank" href="https://go.redav.online/a60ef997f3737650?erid=LdtCK2DsV&m=7"><img src="/img/nadpo'+dm+'.png" alt="" style="max-width: 100%;"></a></div>';
    return 0; }

  if (ND[camp+':disabled'] == 1) { return ''; }
  let adid = ad;
  if (str(adid) == '') { adid = nacnext(camp); }
  if (str(adid) == '') { return ''; }
  let res = nacdiv(camp, adid);
  if (res == '') { return ''; }
  if (str(div) == '') { div = 'nac_'+camp; }
  if (document.getElementById(div)) { document.getElementById(div).innerHTML = document.getElementById(div).innerHTML + res; } 
}

function nacnext (camp)
{
  let nmin = 0;
  let nmax = int(ND[camp+':nmax']);
  let show = nmin;
  if (nmin != nmax) {
    show = int(getSVar('nc'+camp));
    if (show > nmax) { show = nmin; }
    setSVar('nc'+camp, show+1); }
  return ND[camp+show];
}

function nacdiv (camp, ad) 
{
  let tmin = 0;
  if (ND[ad+':nmin'] != undefined) { tmin = Number(ND[ad+':nmin']); }
  let tmax = tmin;
  if (ND[ad+':nmax'] != undefined) { tmax = Number(ND[ad+':nmax']); }
  let tid = tmin;
  if (tmax > tmin) { tid = getRandomInt(tmin, tmax); }
  let text = ND[ad+':t'+tid];
  let prtnr = ND[ad+':partner'];
  if (ND['partner:'+prtnr+':disabled'] == 1) { return ''; }
  let rekl = 'Реклама. '+ND['partner:'+prtnr+':name']+' ИНН '+ND['partner:'+prtnr+':inn'];
  let style = '';
  if (ND[ad+':style'] != undefined) { style = '.nacad'+ad+ ' { '+ND[ad+':style']+'}'; }
  if (ND[ad+':stylespan'] != undefined) { style = style + '.nacad'+ad+ ' span { '+ND[ad+':stylespan']+'}'; }
  if (style != '') { style = '<style>'+style+'</style>'; }
  let erid = str(ND[ad+tid+':erid']);
  if (erid == "") { erid = str(ND[ad+':erid']); }
  if (erid == "") { return ""; }
  V['_nacdiv'] = int(V['_nacdiv']) + 1;
  let res = style + '<div id="nac'+V['_nacdiv']+'" class="reel reel_'+camp+'"><a class="nac'+camp+
    '" id="naca'+V['_nacdiv']+'" href="/eurl?p=na'+ND[ad+':prefix']+tid+'&erid='+erid+
    '" target="_blank"><div id="nacat'+V['_nacdiv']+'" class="nac'+camp+' nacad'+ad+'">'+text+'</div></a><div class="nacr">'+rekl+'</div></div>';
  return res;
}

function nacres ()
{
  if (vlux == -1) { return; }
  let uk = getLocal('uKind');
  if (uk != 'R' && document.getElementById('resWarn')) {
    let wrn = document.getElementById('resWarn').innerHTML;
    if (!(ND['partner:psypsy:disabled'])) {
      let prtnr = 'psypsy';
      wrn = wrn + '<a href="'+ND['partner:'+prtnr+':inpp']+'" target="_blank">профессиональным психологом</a>.';
      document.getElementById('nacppw').innerHTML = 'Реклама. '+ND['partner:'+prtnr+':name']+' ИНН '+ND['partner:'+prtnr+':inn']; }
    else { wrn = wrn + 'профессиональным психологом.'; }
    document.getElementById('resWarn').innerHTML = wrn; } 
  if (uk == 'R') { ui('resWarn', 'none'); }
  let ii = getRandomInt(1,2);
  if (ii == 2) { nac('res','rwt'); } 
  if (ii == 1) { nac('res','rpp'); } 
/*  nac('res','rmp'); */
  if (uk != "" || getLocal('uRZ') > 15) { return; }
  if (ii == 1) { nac('res','rwt'); } 
  if (ii == 2) { nac('res','rpp'); } 
}

function ttw (text, size) {
  var tag = document.createElement('div');
  tag.style.position = 'absolute';
  tag.style.left = '-99in';
  tag.style.whiteSpace = 'nowrap';
  tag.innerHTML = text;
  document.body.appendChild(tag);
  if (tag.clientWidth > size) { tag.innerHTML = tag.innerHTML.replace(/^(.+?) \S+ (\S+)$/, "$1 .$2"); }
  if (tag.clientWidth > size) { tag.innerHTML = tag.innerHTML.replace(/^(.+?) \S+ (\S+)$/, "$1 .$2"); }
  if (tag.clientWidth > size) { tag.innerHTML = tag.innerHTML.replace(/^(.+?) \S+ (\S+)$/, "$1 .$2"); }
  document.body.removeChild(tag);
  return tag.innerHTML.replace(/\.+(\S+)$/, "... $1");
}

function shv (id) {
  id.style.whiteSpace = id.style.whiteSpace == 'normal' ? 'nowrap': 'normal'; }

function userGenList ()
{
  if (!vuser) { return; }
  let ukind = getLocal('uKind');
  let usort = int(getLocal('u'+ukind+'LogSort'));
  let items = LA[1];
  let tests = LA[2];
  let html = '';
  let glast = '';
  let divg = '<div class="utGrid' + ukind + ' utGS' + ukind + usort + '">';
  let tsort = document.getElementById('unTest');
  let told = tsort.value;
  let tfilter = '';
  if (tsort) { tsort.innerHTML = '<option value="" selected>все тесты</option>'; }

  TA = [];
  let TS = [];
  for (i = 0; i <= tests - 1; i++) { 
    TA[LA[3+i*3]] = LA[4+i*3];
    ttl = LA[5+i*3];
    TN[LA[3+i*3]] = ttl;
    TS[LA[3+i*3]] = usort == 11 ? ttl : ttw(ttl, 380);
    if (tsort) {
      let opt = document.createElement('option');
      opt.value = LA[3+i*3];
      opt.innerHTML = LA[5+i*3];
      tsort.appendChild(opt); }
    if (TA[told]) { tsort.value = told; } }
  tfilter = tsort ? tsort.value : ''; 
  CSV = '';
  let vlnote = 0;
  let ii = 3 + tests*3;
  for (i = 0; i <= items - 1; i++) {
    if (tfilter != '' && LA[ii+1] != tfilter) { ii = ii + 6; continue; }
    let day = textDate(LA[ii], true);
    let tst = LA[ii+1] == 'aaaA' ? 'Анкета' : '<a href="/'+TA[LA[ii+1]]+'.html">'+TS[LA[ii+1]]+'</a>';
    let res = '/result?v=' + LA[ii+1] + LA[ii+2];
    let usr = LA[ii+3];
    let usred = true;
    if (ukind == 'U' && usr.startsWith('#')) {
      usred = false;
      usr = usr.substring(1); usr = '<a target="_blank" href="/study.html?b='+usr+'">Исследование-'+usr+'</a>'; }
    if (usort >= 10) {
      let grp = usort == 10 ? textDate(LA[ii]) : usort == 11 ? tst : usr;
      if (glast != grp) {
        html = html + (html == '' ? '' :  '</div>') + '<div class="utGroup">' + grp + '</div>' + divg;
        glast = grp; }
      if (usort == 11) { tst = ''; }
      else if (usort == 12) { usr = ''; } }
    let mark = '&check;';
    let cans = "";
    if (ukind == 'R' && res.includes('b=')) { try {
      mark = '&#10004;';
      let bqa = res.match(/\&b=([^\=\&]+)/)[1];
      let wmax = bqa.substring(0,1);
      if (wmax >= 'A') { wmax = wmax.charCodeAt(0)-54; }
      cans = encodec(bqa.substring(1), 64, int(wmax));
      cans = cans.substring(2).split('').join('|');
    } catch (e) { } }
    CSV = CSV + '"'+TN[LA[ii+1]]+'","'+day+'","'+usr+'","https://psytests.org'+res+'","'+cans+'"';
    let vl = LA[ii+5];
    let sx = '';
    if (vl != '') {
      sx = vl.slice(0,1); sx = sx == 'F' ? 'Ж' : sx == 'M' ? 'М' : sx == 'N' ? ' ' : '';
      vl = vl.substring(2); 
      CSV = CSV + ',"'+sx+'"';
      if (LA[ii+1] == 'aaaA') { CSV = CSV + ',"'+vl+'"'; }
      else {
        let vla = vl.split(' ');
        for (j = 0; j < vla.length; j++) { CSV = CSV + ',"'+vla[j].replace('.',',')+'"'; } }
    }
    CSV = CSV + "\n";
    let id = LA[ii+4];
    if (usort == 10) { day = day.replace(/(\d\d\.\d\d\.\d\d\d\d, )/, ""); }
    html = html + '<div class="utLog" id="di'+id+'"><div class="utTt">'+tst+'</div><div class="utDt">'+mark+
    '&nbsp;<a target="_blank" href="'+res+'">'+day+'</a></div><div class="utCm"><div id="lc'+id+'">'+usr+
    '</div>'+(usred ? '&nbsp;<div id="lp'+id+'" class="iPen" onclick="logModC('+id+');"></div>' : '')+'</div>'+
    (ukind == 'R' ? '<div class="utSx">'+sx+'</div><div class="utVl" onclick="shv(this);">'+vl+'</div>' : '')+
    '<div class="iTrash" onclick="logDelC('+id+',\''+day+'\');"></div></div>';
    ii = ii + 6; }
  document.getElementById('utList').innerHTML = (usort >= 10 ? '' : divg) + html + '</div>';
}

function logDelC (id, date) {
  return uiConfirm('logDel('+id+');', 'Удалить результат теста от '+date+'?', 'Удалить', 'Отмена'); }
function logDel (id) {
 xhrReq('a=xlog&l='+id+'&m=d&tkn='+getLocal('uTkn'), false, function (resp) {
   document.getElementById('di'+id).style.display = 'none'; });
 ui('uiConfirmation', 'none'); }

function logModC (id) {
  let c = document.getElementById('lc'+id).innerHTML;
  if (c == 'Анонимно') { c = ''; }
  return uiConfirm('logMod('+id+');', '<input id="logmodc" type="text" maxlength=20 value="'+c+'">', 'Сохранить', 'Отмена'); }
function logMod (id) {
  let co = document.getElementById('lc'+id).innerHTML;
  let cn = document.getElementById('logmodc').value;
  if (co == cn) { ui('uiConfirmation', 'none'); return; }
  xhrReq({'a':'xlog','l':id,'m':'c','cc':cn,'tkn':getLocal('uTkn')}, false, function (resp) {
    document.getElementById('lc'+id).innerHTML = cn;
    ui('uiConfirmation', 'none'); }); }

function toB64 (str) {
  let r = btoa(encodeURIComponent(str).replace(/%([0-9A-F]{2})/g, function toSolidBytes(match, p1) { return String.fromCharCode('0x' + p1); }));
  r = r.replaceAll('+',':');
  return r.replaceAll('=','+'); }

function fromB64 (str) {
  let r = str.replaceAll('%2B','+');
  r = r.replaceAll('+','=');
  r = r.replaceAll(':','+');
  return decodeURIComponent(atob(r).split('').map(function(c) { return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2); }).join('')); }

function starlit (mode) {
  document.getElementById('fStar').innerHTML = '&nbsp;<a href="#" onclick="return star(' + (mode == 0 ? 1 : 0) +');">' +
   (mode == 0 ? '&#9734;' : '&#9733;') + '</a>'; }

function star (mode) 
{
  if (!vuser) { return; }
  let star = -1;
  if (mode == 2) { 
    xhrReq('a=tfav&t='+V['code']+'&m=c&tkn='+getLocal('uTkn'), 'none', function(resp) {
      if (resp == '0|1') { starlit(1); } else if (resp == '0|0') { starlit(0); } }); }
  else if (mode == 1) {
    xhrReq('a=tfav&t='+V['code']+'&m=s&tkn='+getLocal('uTkn'), 'none', function(resp) {
      if (resp == '0|ok') { starlit(1); } }); }
  else if (mode == 0) {
    xhrReq('a=tfav&t='+V['code']+'&m=r&tkn='+getLocal('uTkn'), 'none', function(resp) {
      if (resp == '0|ok') { starlit(0); } }); }
  return false;
}

function dizaxp (ttl) {
  setLocal('diza', (new Date().getTime()) + 1000*ttl); }

function studyInit ()
{
  let id = '';
  let bn = '';
  let s = window.location.search;
  if (s != "" && s.charAt(0) == '?') { s = s.substring(1); } else { s = ""; }
  if (s != "" && s.includes('=')) {
    s = '&' + s;
    let r2 = s.match(/\&b=(\d+)/);
    if (r2) { id = r2[1]; }
    let r3 = s.match(/\&n=([^\=\&]+)/);
    if (r3) { bn = r3[1]; } }
  if (id == '') { return; }
  let gsv = getSVar('bn'+id);
  setSVar('bn'+id, '');
  if (bn == "" && gsv != "") { document.location = '/study.html?b='+id+'&n='+gsv; return; }
  let dbn = "";
  if (bn != "") { try { dbn = fromB64(bn); } catch (e) { return errOr('debase'); } } 
  let gl = getLocal('batDone'+id);
  if (dbn != "") { 
    let xhr = new XMLHttpRequest();
    xhr.open('POST', '/user', false);
    xhr.send('a=xstu&b='+id+'&n='+encodeURIComponent(dbn)+'&m=n');
    if (xhr.status == 200) {
      bb = xhr.responseText.trim();
      if (bb.startsWith('0|')) { gl = bb.substring(2); } } }
  let utkn = getLocal('uTkn');
  xhrReq('a=gstu&b='+id+(bn == '' ? '' : '&n=1')+(utkn != '' ? '&tkn='+utkn : ''), false, function (resp) {
    let ar = resp.split('|');
    let tnum = ar[1];
    let name = '<div>' + ar[2] + '</div>';
    if (ar[3] != '') { name = name + '<span>результаты получит</span><div>' + ar[3] + '</div>'; }
    document.getElementById('stuName').innerHTML = name;
    if (ar[5] != '') { document.getElementById('stuNote').innerHTML = '<p>' + ar[5] + '</p>'; ui('stuNote'); }
    ui('stuName', 'flex');
    document.title = document.title + ' #' + id;
    document.querySelector('meta[name="description"]').setAttribute('content', 'Психологическое исследование №' + id + '. ' + ar[2]);
    document.getElementById('pageH1').innerHTML = document.getElementById('pageH1').innerHTML + ' №' + id;
    document.getElementById('pageHdr').style.display = 'block';
    let ii = 6;
    let html = '';
    for (i=0; i<tnum; i++) {
      let uri = ar[ii+1] + '-run.html?bat=' + id;
      if (bn != '') { uri = uri + '&bn=' + bn; }
      if (str(ar[ii+3]) != "") { uri = uri + '&f='+ar[ii+3]; }
      let done = gl.includes(ar[ii]+'_') ? ' style="opacity: 50%"' : '';
      html = html + '<div'+done+'><a href="/' + uri + '">'+ar[ii+2]+'</a></div>';
      ii = ii + 4; }
    if (ar[ii].includes('A7')) { dizaxp(7200); }
    if (html != '') { document.getElementById('stuTL').innerHTML = html; }
    if (!ar[4].includes('N1') && !ar[4].includes('SELF') && !bn) {
      ui('stuWarn'); 
      showAnonID(); }
  });
}

function textDate (ux, hm) {
  let uday = new Date(ux*1000);
  if (hm) { return uday.toLocaleString('ru', {year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute:'2-digit'}); }
  return uday.toLocaleString('ru', {year: 'numeric', month: '2-digit', day: '2-digit'}); }

function uiSw (p) { return int(V['uisw_'+p]); } 

function testRerun (name) {
  ui('uiConfirmation', 'none'); 
  if (document.getElementById('uiConfNA').checked) { setLocal('RerunNA', 1); }
  document.location = document.getElementById('uredo').href; }
function testRerunC (name) {
  if (getLocal('RerunNA') == 1) { return true; }
  uiConfirm('testRerun();', (ven ? 'Cancel the assessment?' : 'Прервать прохождение теста?'), (ven ? 'Yes' : 'Да'), (ven ? 'No' : 'Нет')); 
  document.getElementById('uiAddon').innerHTML = '<input type="checkbox" id="uiConfNA"> '+(ven ? 'Don\'t ask again.' : 'Больше не спрашивать');
  return false; }

function uiConfirm (ifok, msg, ok, cancel, cb) {
  document.getElementById('uiConf').innerHTML = 
  '<div>'+(cb ? '<input type="checkbox" id="uiConfCB" onchange="uiConfirmCB();"> ' : '')+msg+
  '</div><div id="uiConfYN"><input id="uiConfOK" type="button" value="'+ok+'" onclick="'+ifok+'"'+
  (cb ? ' disabled' : '')+'> <input type="button" value="'+cancel+
  '" onclick="ui(\'uiConfirmation\', \'none\'); return false;">' +
  '</div><div id="uiAddon"></div>';
  ui('uiConfirmation', 'flex');
  return false; }

function uiConfirmCB () {
  document.getElementById('uiConfOK').disabled = !document.getElementById('uiConfCB').checked; }

function uiSwitch (p, v) {
  for (ii = 0; ii <= 5; ii++) {
    if (document.getElementById('uisw'+p+ii)) {
      document.getElementById('uisw'+p+ii).className = v == ii ? 'uiSwSel' : ''; } }
  V['uisw_'+p] = v; }

function ui (p, v) {
  if (document.getElementById(p)) {
    document.getElementById(p).style.display = v != undefined ? v : 'block'; } }

function uinone (p) {
  if (document.getElementById(p)) {
    if (window.getComputedStyle(document.getElementById(p), null).display == 'none') { return true; } }
  return false; }

function userLogMeOut() {
  dizaxp(0);
  userLogout();
  document.location = '/'; }

function csvDownload () {
  const blob = new Blob([CSV], {type:'text/csv'}); 
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  let op = document.getElementById('unBat');
  let fn = op ? op.options[op.selectedIndex].text : 'мои данные';
  a.setAttribute('href', url);
  a.setAttribute('download', fn + '.csv'); 
  a.click(); }
