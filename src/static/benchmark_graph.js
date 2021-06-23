// global constants
const range = (start, stop, step) => Array.from({ length: (stop - start - 1) / step + 1}, (_, i) => start + (i * step));
const socket = new WebSocket('ws://localhost:8000/ws/benchmark/');
const job_entry = `{{ model_name }}
        <div class="dropdown" id="field-{{ job_id }}">
            <button class="btn btn-secondary dropdown-toggle" type="button" id="dropdown-{{ job_id }}" data-bs-toggle="dropdown" aria-expanded="false">
            </button>
            <ul class="dropdown-menu" aria-labelledby="dropdown-{{ job_id }}" id="buttons-{{ job_id }}">

            </ul>
        </div>
`;
var chart;
const dataMap = new Map();
const data = {
    labels: [],
    datasets: []
  };
const graphData = {
    type: 'bar',
    data: data,
    options: {
        responsive: true,
        scales: {
            y: {
              beginAtZero: true
            }
          },
    },
};
var modeltable;
const jobMap = new Map(); // map of job_id -> (map of key -> value (keys = ["title", ""]))

// methods
function new_job_entry(job_id) {
    const div = document.createElement('div');
    div.className = "d-flex justify-content-center btn-group";
    div.innerHTML = job_entry.replace("{{ model_name }}", jobMap.get(job_id).get("title")).replace("{{ job_id }}", job_id.toStr())
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
    const job_entry = jobMap.get(job_id).get("job_entry");
    if (job_entry.parentNode != modeltable) {
        modeltable.appendChild(job_entry);
    }
}

function hidejobEntry(job_id) {
    const job_entry = jobMap.get(job_id).get("job_entry");
    modeltable.removeChild(job_entry);
}

function rebuildChart() {
    // get active jobs with a non empty active field name
    const labels = [];
    const scores = [];
    for (const [job_id, jobdata] of jobMap.entries()) {
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
    chart.update();
}

function updateChart(job_id, result_field) {
    const jobdata = jobMap.get(job_id);
    jobdata.set("active_field", result_field);
    const results = jobdata.get("results");
    dataMap.set(job_id, results.get[result_field])
    rebuildChart();
}

socket.onmessage = function(e) {
    const eventData = JSON.parse(e.data);
    const job_id = eventData.id;
    const result_fields = Object.keys(eventData.result);
    const jobdata = jobMap.get(job_id);
    const results = jobdata.get("results");
    const job_entry = jobdata.get("job_entry");
    const buttons = [];
    for (const field of result_fields) {
        buttons.push(field_button(field, job_id));
        results.set(field, eventData.result[field]);
    }
    jobdata.set("buttons", buttons);
    const dropdown = job_entry.getElementById("dropdown-".concat(job_id.toStr()));
    const buttonlist = job_entry.getElementById("buttons-".concat(job_id.toStr()));
    for (const button of buttons) {
        button.button.addEventListener("click", function(){
            for (const b of buttons) {
                b.button.className = b.button.className.replace(" active", "");
            };
            button.button.className += " active";
            dropdown.innerText = button.button.innerText;
            jobdata.set("active_field")
            updateChart(button.job_id, button.result_field);
        })
        buttonlist.appendChild(button.li);
    }
    jobdata.set("loaded", true);
    if (jobdata.get("active")) {
        showjobEntry(job_id);
    }
}

window.addEventListener("load", function(){
    const jobs_list = JSON.parse(jobs_with_benchmark_str);
    for (const job of jobs_list) {
        const new_map = new Map();
        new_map.set("title", job.mlmodel__title);
        new_map.set("results", new Map());
        new_map.set("active_field", null);
        const job_entry = new_job_entry(job.id);
        new_map.set("job_entry", job_entry);
        jobMap.set(job.id, new_map);
    }
    const checkboxes = document.getElementsByClassName("bench-select");
    for (const checkbox in checkboxes) {
        const checkbox_id = checkbox.id;
        const x = checkbox_id.split("-");
        const job_id = parseInt(x[x.length - 1]);
        const job_data = jobMap.get(job_id);
        job_data.set("active", false);
        checkbox.addEventListener("change", function () {
            job_data.set("active", checkbox.active);
            if (checkbox.active) {
                if (job_data.get("loaded")) {
                    showjobEntry(job_id);
                } else {
                    socket.send(job_id.toStr());
                }
            } else {
                hidejobEntry(job_id);
            };
        });
    }
    const ctx = div.getElementById('chart');
    chart = new Chart(ctx, graphData);
    modeltable = this.document.getElementById('modeltable');
});