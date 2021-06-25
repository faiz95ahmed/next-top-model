// globals
const b64toBlob = (base64, type = 'application/octet-stream') => fetch(`data:${type};base64,${base64}`).then(res => res.blob())
const socket = new WebSocket('ws://localhost:8000/ws/benchmark/');
const job_entry = `{{ model_name }}
        <div class="dropdown" id="field-{{ job_id }}">
            <button class="btn btn-secondary dropdown-toggle" type="button" id="dropdown-{{ job_id }}" data-bs-toggle="dropdown" aria-expanded="false">
            </button>
            <ul class="dropdown-menu" aria-labelledby="dropdown-{{ job_id }}" id="buttons-{{ job_id }}">

            </ul>
        </div>
`;
const table = `\\begin{center}
\\begin{tabular}{|c|c|c|c|} 
\\hline
{{ fields }} \\\\ [0.5ex] 
\\hline\\hline
{{ data }}
\\end{tabular}
\\end{center}`
// const dataMap = new Map();
var chart;

var chartString ="";
const data = {
    labels: [],
    datasets: []
  };
const graphData = {
    type: 'bar',
    data: data,
    options: {
        animation: {},
        plugins: {
            legend: {
                display: false
            }
        },
        scales: {
            y: {
              beginAtZero: true
            }
          },
    },
};

var ctx = document.getElementById('chart');
while (ctx === null) {
    ctx = document.getElementById('chart');
    
}
chart = new Chart(ctx, graphData);

while (modeltable === null) {
    modeltable = document.getElementById('modeltable');
}

var chartToClipboardButton = document.getElementById('chartToClipboard');
while (chartToClipboardButton === null) {
    chartToClipboardButton = document.getElementById('chartToClipboard');
}
chartToClipboardButton.addEventListener("click", copyChartToClipboard)

var dataToLatexButton = document.getElementById('dataToLatex');
while (dataToLatexButton === null) {
    dataToLatexButton = document.getElementById('dataToLatex');
}
dataToLatexButton.addEventListener("click", copyDataToLatex)

var decimal_precision = 2;

function round(x) {return Math.round((10**decimal_precision) * x) / (10**decimal_precision)}

const jobMap = new Map(); // map of job_id -> (map of key -> value (keys = ["title", ""]))

// methods
function new_job_entry(job_id, title) {
    // console.log(job_id);
    const div = document.createElement('div');
    div.className = "d-flex justify-content-center btn-group";
    div.innerHTML = job_entry.replaceAll("{{ model_name }}", title).replaceAll("{{ job_id }}", job_id.toString())
    return div;
}

function field_button(result_field, job_id) {
    const li = document.createElement('li');
    const button = document.createElement('button');
    button.className = "dropdown-item ".concat(result_field.concat("button"));
    button.type = "button";
    button.innerText = result_field;
    li.appendChild(button);
    return {li:li, button:button, job_id:job_id, result_field:result_field};
}

function showjobEntry(job_id) {
   //  console.log("showing " +job_id.toString());
    const job_entry = jobMap.get(job_id).get("job_entry");
    if (job_entry.parentNode != modeltable) {
        modeltable.appendChild(job_entry);
    }
}

function hidejobEntry(job_id) {
    const job_entry = jobMap.get(job_id).get("job_entry");
    if (job_entry.parentNode == modeltable) modeltable.removeChild(job_entry);
}

function rebuildChart() {
    // get active jobs with a non empty active field name
    const labels = [];
    const scores = [];
    for (const jobdata of jobMap.values()) {
        const active_field = jobdata.get("active_field")
        if (jobdata.get("active") & (active_field != "")) {
            labels.push(jobdata.get("title"));
            scores.push(jobdata.get("results").get(active_field));
        }
    };
    const datasets = [{
        data: scores,
        backgroundColor: Array(data.length).fill('rgba(54, 162, 235, 0.5)'),
        borderColor: Array(data.length).fill('rgba(54, 162, 235, 1)'),
        borderWidth: 1
    }];
    data.labels = labels;
    data.datasets = datasets;
    chart.config._config.options.animation = {onComplete: enableChartCopyButton};

    // disable copy to clipboard button
    disableChartCopyButton()
    chart.update();
}

function disableChartCopyButton() {
    chartToClipboardButton.disabled = true;
    console.log(chart.height, chart.width)
}

function enableChartCopyButton() {
    chartToClipboardButton.disabled = false;
}

function copyChartToClipboard() {
    chart.canvas.toBlob(blob => navigator.clipboard.write([new ClipboardItem({'image/png': blob})]));
}

function getLatexTableString() {
    const fields = [];
    // var models = [];
    for (const jobdata of jobMap.values()) {
        for (const field of jobdata.get("results").keys()) {
            if (!fields.includes(field)) fields.push(field)
        }
    }
    const field_str = "Model & "+ fields.join(" & ");
    const row_strings = [];
    for (const jobdata of jobMap.values()) {
        var row = [jobdata.get("title")];
        const results = jobdata.get("results");
        for (const field of fields) {
            if (results.has(field)) {
                row.push(round(results.get(field)));
            } else {
                row.push("N/A");
            }
        }
        row_strings.push(row.join(" & "));
    }
    row_strings.push("\\hline")
    const all_rows = row_strings.join(" \\\\\n"); 
    return table.replace("{{ fields }}", field_str).replace("{{ data }}", all_rows);
}

function copyDataToLatex() {
    navigator.clipboard.writeText(getLatexTableString());
}

function updateChart(job_id, result_field) {
    const jobdata = jobMap.get(job_id);
    jobdata.set("active_field", result_field);
    // const results = jobdata.get("results");
    // dataMap.set(job_id, results.get[result_field])
    rebuildChart();
}

socket.onmessage = function(e) {
    const eventData = JSON.parse(e.data);
    // console.log(eventData)
    const job_id = eventData.id;
    const result_fields = Object.keys(eventData.content);
    const jobdata = jobMap.get(job_id);
    const results = jobdata.get("results");
    // const job_entry = jobdata.get("job_entry");
    const buttons = [];
    for (const field of result_fields) {
        buttons.push(field_button(field, job_id));
        results.set(field, eventData.content[field]);
    }
    jobdata.set("loaded", true);
    if (jobdata.get("active")) {
        // console.log("Delayed showing");
        showjobEntry(job_id);
    }
    jobdata.set("buttons", buttons);
    const dropdown = document.getElementById("dropdown-".concat(job_id.toString()));
    const buttonlist = document.getElementById("buttons-".concat(job_id.toString()));
    for (const button of buttons) {
        button.button.addEventListener("click", function(){
            for (const b of buttons) {
                b.button.className = b.button.className.replaceAll(" active", "");
            };
            button.button.className += " active";
            dropdown.innerText = button.button.innerText;
            jobdata.set("active_field")
            updateChart(button.job_id, button.result_field);
        })
        buttonlist.appendChild(button.li);
    }

}

window.addEventListener("load", function(){
    const jobs_list = JSON.parse(gl_jobsWithBenchmarkStr);
    for (const job of jobs_list) {
        const new_map = new Map();
        new_map.set("title", job.mlmodel__title);
        new_map.set("results", new Map());
        new_map.set("active_field", null);
        const job_entry = new_job_entry(job.id, job.mlmodel__title);
        new_map.set("job_entry", job_entry);
        jobMap.set(job.id, new_map);
    }
    const checkboxes = document.getElementsByClassName("bench-select");
    for (const checkbox of checkboxes) {
        // console.log("CHECKBOXES!!!!")
        const checkbox_id = checkbox.id;
        const x = checkbox_id.split("-");
        const job_id = parseInt(x[x.length - 1]);
        const job_data = jobMap.get(job_id);
        job_data.set("active", false);
        checkbox.addEventListener("change", function () {
            // console.log(checkbox.checked)
            job_data.set("active", checkbox.checked);
            if (checkbox.checked) {
                if (job_data.get("loaded")) {
                    // console.log("Instant showing");
                    showjobEntry(job_id);
                } else {
                    // console.log("Loading");
                    socket.send(job_id.toString());
                }
            } else {
                hidejobEntry(job_id);
            };
        });
    }
});