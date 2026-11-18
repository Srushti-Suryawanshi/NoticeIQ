const dz=document.getElementById('dropZone'), fi=document.getElementById('fileInput');
if(dz&&fi){dz.addEventListener('click',e=>{if(e.target.tagName!=='LABEL')fi.click()});['dragenter','dragover'].forEach(ev=>dz.addEventListener(ev,e=>{e.preventDefault();dz.classList.add('dragging')}));['dragleave','drop'].forEach(ev=>dz.addEventListener(ev,e=>{e.preventDefault();dz.classList.remove('dragging')}));dz.addEventListener('drop',e=>{if(e.dataTransfer.files.length){fi.files=e.dataTransfer.files;showFile()}});fi.addEventListener('change',showFile);function showFile(){document.getElementById('fileName').textContent=fi.files[0]?.name||''}}
const uf=document.getElementById('uploadForm');if(uf)uf.addEventListener('submit',()=>{const b=document.getElementById('processBtn');b.disabled=true;b.innerHTML='Analyzing…';document.getElementById('uploadProgress').classList.remove('d-none')});
function useSuggestion(el){const i=document.getElementById('chatInput');i.value=el.textContent;i.focus()}
const dataEl=document.getElementById('calendarData');if(dataEl){const events=JSON.parse(dataEl.textContent);let cursor=new Date();cursor.setDate(1);const days=document.getElementById('calendarDays'),label=document.getElementById('monthLabel');function render(){days.innerHTML='';label.textContent=cursor.toLocaleDateString(undefined,{month:'long',year:'numeric'});const first=new Date(cursor.getFullYear(),cursor.getMonth(),1).getDay(),count=new Date(cursor.getFullYear(),cursor.getMonth()+1,0).getDate();for(let i=0;i<first;i++){const x=document.createElement('div');x.className='calendar-cell muted-cell';days.append(x)}for(let d=1;d<=count;d++){const dateKey=`${cursor.getFullYear()}-${String(cursor.getMonth()+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`,matches=events.filter(e=>e.date===dateKey);const cell=document.createElement('div');cell.className='calendar-cell'+(dateKey===new Date().toISOString().slice(0,10)?' today':'');cell.innerHTML=`<span>${d}</span>`;matches.forEach(e=>{const tag=document.createElement('small');tag.className='calendar-event';tag.textContent=e.title;tag.title=e.title+' · '+e.type;cell.append(tag)});days.append(cell)}const list=document.getElementById('eventList');list.innerHTML='';events.sort((a,b)=>a.date.localeCompare(b.date)).forEach(e=>{const row=document.createElement('div');row.className='event-row';const date=new Date(e.date+'T00:00:00');row.textContent=date.toLocaleDateString(undefined,{day:'numeric',month:'short',year:'numeric'})+' · '+e.title+' · '+e.type;list.append(row)});if(!events.length)list.textContent='No dates yet. Save notices with dates or add tasks with due dates.'}document.getElementById('prevMonth').onclick=()=>{cursor.setMonth(cursor.getMonth()-1);render()};document.getElementById('nextMonth').onclick=()=>{cursor.setMonth(cursor.getMonth()+1);render()};document.getElementById('todayBtn').onclick=()=>{cursor=new Date();cursor.setDate(1);render()};render()}


/* ===== NOTICEIQ IMPROVEMENTS ===== */

// Theme switching
const themeToggle = document.getElementById('themeToggle');

if (themeToggle) {
    const savedTheme = localStorage.getItem('noticeiq-theme');

    if (savedTheme === 'dark') {
        document.body.classList.add('dark-theme');
    }

    function updateThemeButton() {
        const isDark = document.body.classList.contains('dark-theme');
        themeToggle.textContent = isDark ? '☀️ Light mode' : '🌙 Dark mode';
    }

    updateThemeButton();

    themeToggle.addEventListener('click', function () {
        document.body.classList.toggle('dark-theme');

        const isDark = document.body.classList.contains('dark-theme');
        localStorage.setItem('noticeiq-theme', isDark ? 'dark' : 'light');

        updateThemeButton();
    });
}

// Show/hide password
const passwordToggle = document.getElementById('passwordToggle');
const passwordInput = document.getElementById('passwordInput');

if (passwordToggle && passwordInput) {
    passwordToggle.addEventListener('click', function () {
        if (passwordInput.type === 'password') {
            passwordInput.type = 'text';
            passwordToggle.textContent = 'Hide';
        } else {
            passwordInput.type = 'password';
            passwordToggle.textContent = 'Show';
        }
    });
}

// Auto-dismiss flash messages after 3.5 seconds
document.querySelectorAll('.flash-wrap .alert').forEach(function (alertBox) {
    setTimeout(function () {
        if (alertBox && alertBox.isConnected) {
            const alertInstance = bootstrap.Alert.getOrCreateInstance(alertBox);
            alertInstance.close();
        }
    }, 3500);
});
