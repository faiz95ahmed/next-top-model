// TODO:
// * Choose a consistent naming convention (i.e. camel case vs underscores)
// * Split up large functions
// * Split up into multiple modules to avoid code duplication with benchmark viewing code
// * Sort out issue with arbitrarily picking the first series to update the progress bar
// * Find a better method of interpolating missing datapoints
// * Find more canonical JS ways of doing things

// global constants
const chart_colours = ['rgb(255, 97, 131)', 'rgb(131, 255, 97)', 'rgb(97, 131, 255)'];
const range = (start, stop, step) => Array.from({ length: (stop - start - 1) / step + 1}, (_, i) => start + (i * step));
const logname_to_level = new Map([["debug", 10], ["info", 20], ["warning", 30], ["error", 40], ["critical", 50]]);
const loglevel_to_name = new Map([[10, "debug"], [20, "info"], [30, "warning"], [40, "error"], [50, "critical"]]);
const socket = new WebSocket('ws://localhost:8000/ws/graph/');
const graph_component = `
    <h1 id="boxtitle-{{ box_num }}"></h1>
    <canvas id="myChart-{{ box_num }}" width="400" height="400"></canvas>
    <div class="progress">
        <div id="progress-bar-{{ box_num }}" class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style="width: 0%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div>
    </div>
    <div class="d-flex justify-content-center btn-group">
        <div class="form-check form-check-inline">
            <input class="form-check-input" type="checkbox" value="" id="showlogtime-{{ box_num }}">
            <label class="form-check-label" for="showlogtime-{{ box_num }}">
                Time
            </label>
        </div>
        <div class="form-check form-check-inline">
            <input class="form-check-input" type="checkbox" value="" id="showlogorder-{{ box_num }}">
            <label class="form-check-label" for="showlogorder-{{ box_num }}">
                Relative Order
            </label>
        </div>
        <div class="dropdown" id="loglevel-{{ box_num }}-div">
            <button class="btn btn-secondary dropdown-toggle" type="button" id="loglevel-{{ box_num }}" data-bs-toggle="dropdown" aria-expanded="false">
              Log Level: INFO
            </button>
            <ul class="dropdown-menu" aria-labelledby="loglevel-{{ box_num }}">
              <li><button class="dropdown-item debugbutton" type="button">DEBUG</button></li> <!-- 10 -->
              <li><button class="dropdown-item infobutton active" type="button">INFO</button></li> <!-- 20 -->
              <li><button class="dropdown-item warningbutton" type="button">WARNING</button></li> <!-- 30 -->
              <li><button class="dropdown-item errorbutton" type="button">ERROR</button></li> <!-- 40 -->
              <li><button class="dropdown-item criticalbutton" type="button">CRITICAL</button></li> <!-- 50 -->
            </ul>
          </div>
    </div>
    <div class="logbox" id="logbox-{{ box_num }}" style="white-space:pre-wrap;height:120px;border:1px solid #ccc;overflow:auto;font-family:monospace;font-size:12px;background-color:black;"></div>
    <div class="d-flex justify-content-center">
        <button class="abortbutton" id="abort-{{ box_num }}"></button>
    </div>
`;

const style_components = [[
    "debug", 
    `.debug{{ box_num }} {
        color:blue;
        display: {{ display }};
        margin-bottom: 0;
    }`],
    ["info",
    `.info{{ box_num }} {
        color:white;
        display: {{ display }};
        margin-bottom: 0;
    }`],
    ["warning",
    `.warning{{ box_num }} {
        color:yellow;
        display: {{ display }};
        margin-bottom: 0;
    }`],
    ["error",
    `.error{{ box_num }} {
        color:red;
        display: {{ display }};
        margin-bottom: 0;
    }`],
    ["critical",
    `.critical{{ box_num }} {
        color:red;
        font-weight: bold;
        display: {{ display }};
        margin-bottom: 0;
    }`]
];

const log_style_options = `
    .logOrder{{ box_num }} {
        display: {{ log_order }}
    }
    .logTime{{ box_num }} {
        display: {{ log_time }}
    }
`;

// global variables & constants pointing to mutable types (which will be changed)
const jobMap = new Map(); // map of job_id -> (labels, dataset, max epoch); dataset is a map of series name -> Array of value (Note, the mapping order is swapped compared to the incoming data)
const job_to_box = new Map(); // int -> int
const box_to_job = new Map(); // int -> int (these two need to be edited in parallel!)
const boxMap = new Map(); // map of box_id (int) -> (title slot, chart context, chart, progress bar, controls, log box, style)
var box_count = 0;
var head = null;

// methods
function freshjobMap() {
    const r = new Map();
    r.set("max_epoch", 0);
    const dataset = new Map();
    r.set("datasets", dataset);
    r.set("labels", []);
    return r;
}

function newStyle(boxNum, logLevel) {
    const styleMap = new Map(style_components);
    for (const lname of styleMap.keys()) {
        var lvlstyle = styleMap.get(lname);
        const level = logname_to_level.get(lname);
        const display = level >= logLevel ? "block" : "none";
        lvlstyle = lvlstyle.replaceAll("{{ box_num }}", boxNum.toString());
        lvlstyle = lvlstyle.replaceAll("{{ display }}", display);
        styleMap.set(lname, lvlstyle);
    }
    return styleMap;
}

function updateStyleTag(boxNum, logLevel) {
    const new_style_map = newStyle(boxNum, logLevel);
    const style_string = Array.from(new_style_map.values()).join("\n");
    var style_section = document.getElementById('loglevelstyle-'.concat(boxNum.toString()));
    if (style_section === null) {
        style_section = document.createElement('style');
        style_section.id = "loglevelstyle-".concat(boxNum.toString());
        head.appendChild(style_section);
    }
    style_section.innerText = style_string;
}

function updateStyleOptionsTag(boxNum) {
    const orderVisibility = boxMap.get(boxNum).logbox.logboxOrderCheckbox.checked ? "inline" : "none";
    const timeVisibility = boxMap.get(boxNum).logbox.logboxTimeCheckbox.checked ? "inline" : "none";
    const style_string = log_style_options.replaceAll("{{ log_order }}", orderVisibility).replaceAll("{{ log_time }}", timeVisibility).replaceAll("{{ box_num }}", boxNum.toString());
    var style_section = document.getElementById('logoptionsstyle-'.concat(boxNum.toString()));
    if (style_section === null) {
        style_section = document.createElement('style');
        style_section.id = "loglevelstyle-".concat(boxNum.toString());
        head.appendChild(style_section);
    }
    style_section.innerText = style_string;
}

function rejigBoxes(active_job_ids) {
    var num_active_jobs = active_job_ids.length;
    var max_count = num_active_jobs;
    var boxes_to_remove  = [];
    var free_boxes = [];
    if (num_active_jobs > box_count) {
        // add a bunch of empty boxes
        free_boxes = range(box_count, num_active_jobs, 1);
        max_count = box_count;
        for (const i of free_boxes) {constructBox(i);};
    } else if (num_active_jobs < box_count) {
        boxes_to_remove = range(num_active_jobs, box_count, 1);
    }
    // determine which slots are free
    for (const i of range(0, box_count, 1)) {
        const job_id = box_to_job.get(i);
        if (!active_job_ids.includes(job_id)) {
            if (i < max_count) {
                free_boxes.push(i);
            }
            jobMap.delete(job_id);
            const box_num = job_to_box.get(job_id);
            const loglevelstyle = document.getElementById('loglevelstyle-'.concat(box_num.toString()));
            const logoptionsstyle = document.getElementById('logoptionsstyle-'.concat(box_num.toString()));
            head.removeChild(loglevelstyle);
            head.removeChild(logoptionsstyle);
            job_to_box.delete(job_id);
        }
    }
    // determine which jobs need to be moved to new slots
    var floating_jobs = [];
    for (const job_id of active_job_ids) {
        if (!job_to_box.has(job_id)) {
            jobMap.set(job_id, freshjobMap());
            floating_jobs.push(job_id);
        }
        if (job_to_box.get(job_id) > num_active_jobs) {
            floating_jobs.push(job_id);
        }
    }
    // assign jobs to free slots
    for (const free_box of free_boxes) {
        const job_id = floating_jobs.pop();
        job_to_box.set(job_id, free_box);
        box_to_job.set(free_box, job_id);
        
    }
    var boxes_to_load = free_boxes; // renaming for clarity
    // delete unused boxes
    for (const i of boxes_to_remove) {
        box_to_job.delete(i);
    }
    box_count = num_active_jobs;
    return {
        "boxes_to_remove": boxes_to_remove, // this is redundant
        "boxes_to_load": boxes_to_load,
    };
}

function disableAbortButton(abortButton) {
    abortButton.innerHTML = '';
    abortButton.disabled = true;
    var newFirstElement = document.createElement('span');
    newFirstElement.setAttribute("class", "spinner-border spinner-border-sm");
    newFirstElement.setAttribute("role", "status");
    newFirstElement.setAttribute("aria-hidden", "true");
    abortButton.appendChild(newFirstElement);
    var newstuff = document.createElement(null);
    newstuff.innerText = "  Waiting for Acknowledgement...";
    abortButton.appendChild(newstuff);
}

function abortAcknowledged(abortButton) {
    abortButton.setAttribute("class", "abortbutton btn btn-success");
    abortButton.innerHTML = "  Abort Acknowledged!";
}

function constructBox(boxNum) {
    // construct box and store elements in boxMap
        // title slot
        // chart & chart context
        // progress bar
        // controls
        // log box
        // style map
    var div = document.createElement('div');
    div.className = "col";
    div.id = "realtimegraphbox-".concat(boxNum.toString());
    var new_box_string = graph_component.replaceAll("{{ box_num }}", boxNum.toString());
    // console.log(new_box_string);
    div.innerHTML = new_box_string.trim();
    const boxData = {
        div: div,
        header: div.getElementsByTagName('h1')[0],
        bar: div.getElementsByClassName('progress-bar')[0],
        abortButton: div.getElementsByClassName('abortbutton')[0],
    };
    console.log(boxData.bar);
    console.log(boxData.abortButton);
    boxMap.set(boxNum, boxData);
    // reconstructBox(boxNum);
    return div;
}

function reconstructBox(boxNum) {
    // reconstruct a box
    // new Title, new Chart
    // reset controls
    // empty log box
    // reset style
    const old_boxdata = boxMap.get(boxNum);
    const header = old_boxdata.header;
    header.innerText = "";
    const div = old_boxdata.div;
    const ctx = div.getElementsByTagName('canvas')[0].getContext('2d');
    const graphData = {
        type: 'line',
        data: {
            labels: jobMap.get(box_to_job.get(boxNum)).get("labels"),
            datasets: []
        },
        options: {
            plugins: {
                legend: {
                    display: true,
                    labels: {
                        color: 'rgb(0, 0, 0)'
                    }
                }
            }
        }
    };
    const styleMap = newStyle(boxNum, 20);
    const chart = new Chart(ctx, graphData);
    const logLevelDropdown = div.getElementsByClassName("dropdown")[0];
    const logLevelName = div.getElementsByClassName("dropdown-toggle")[0];
    const loglevelButtonMap = new Map();
    const loglevelButtons = [];
    for (const lvlName of logname_to_level.keys()) {
        const button = logLevelDropdown.getElementsByClassName(lvlName.concat("button"))[0];
        loglevelButtonMap.set(lvlName, button);
        loglevelButtons.push(button);
    }
    for (const [lvlName, lvl] of logname_to_level.entries()) {
        const button = loglevelButtonMap.get(lvlName);
        // this is my first time with JS, but I'm hoping the variables lvl, button, loglevelButtons,
        // and boxNum get properly bound into the anonymous function 
        button.addEventListener("click", function(){
                    for (const b of loglevelButtons) {
                        b.className = b.className.replaceAll(" active", "");
                    };
                    button.className += " active";
                    logLevelName.innerText = "Log Level: ".concat(lvlName.toUpperCase())
                    updateStyleTag(boxNum, lvl);
                })
    }
    const checkboxes = div.getElementsByClassName("form-check-input");
    const index_for_time_checkbox = checkboxes[0].id == "showlogtime-".concat(boxNum) ? 0 : 1;
    const logboxTimeCheckbox = checkboxes[index_for_time_checkbox];
    logboxTimeCheckbox.addEventListener("change", function(){updateStyleOptionsTag(boxNum);});
    const logboxOrderCheckbox = checkboxes[1 - index_for_time_checkbox];
    logboxOrderCheckbox.addEventListener("change", function(){updateStyleOptionsTag(boxNum);});
    const logboxElement = div.getElementsByClassName("logbox")[0];
    logboxElement.innerHTML = '';
    const logbox = {
        logboxElement: logboxElement,
        logboxTimeCheckbox: logboxTimeCheckbox,
        logboxOrderCheckbox: logboxOrderCheckbox,
        logLevelDropdown: logLevelDropdown,
        loglevelButtonMap: loglevelButtonMap,
        loglevelButtons: loglevelButtons
    };
    
    updateStyleTag(boxNum, 20);
    old_boxdata.abortButton.setAttribute("class", "abortbutton btn btn-danger");
    old_boxdata.abortButton.disabled = false;
    old_boxdata.abortButton.innerHTML = "Abort";
    const job_id = box_to_job.get(boxNum);
    old_boxdata.abortButton.addEventListener("click", function() {
        if (confirm('Are you sure you want to abort job ' + job_id + "?")) {
            $.ajax(
            {
                type:"GET",
                url: "{% url 'graph:graph-abort' %}",
                data:{
                    job_id: job_id
                },
                success: function( data ) 
                {
                    disableButton(abortButton)
                }
            })
        } else {
            return false;
        }
    });
    setProgress(old_boxdata.bar, 0, "");
    const new_box_data = {
        div: old_boxdata.div,
        header: old_boxdata.header,
        ctx: ctx,
        chart: chart,
        bar: old_boxdata.bar,
        logbox: logbox,
        abortButton: old_boxdata.abortButton,
        styleMap: styleMap
    };
    boxMap.set(boxNum, new_box_data);
    updateStyleOptionsTag(boxNum);
}

function constructRow(rowNum, numBoxesInRow) {
    var div = document.createElement('div');
    div.className = "row align-items-start";
    div.id = "row-".concat(rowNum.toString());
    var boxes = [constructBox(2 * rowNum)];
    if (numBoxesInRow > 1) {
        boxes.push(constructBox((2 * rowNum) + 1));
    }
    for (const box of boxes) {
        div.appendChild(box);
    }
    return div;
}

function resizeGrid(numBoxes) {
    var gridElem = document.getElementById('graphGrid');
    var rows = gridElem.children;
    const num_rows = (numBoxes + 1) >> 1;
    console.log(num_rows.toString() + " " + rows.length.toString());
    if (rows.length > num_rows) {
        for (const i of range(num_rows, rows.length)) {
            gridElem.removeChild(rows.item(i));
        }
    }
    else if (rows.length < num_rows) {
        console.log("HELLO");
        console.log(range(rows.length, num_rows, 1));
        for (const i of range(rows.length, num_rows, 1)) {
            var new_row;
            if (i == (num_rows - 1)) {
                new_row = constructRow(i, numBoxes % 2);
            } else {
                new_row = constructRow(i, 2);
            }
            gridElem.appendChild(new_row);
            console.log("appended");
        }
    } else if (rows.length > 0) {
        // correct number of rows. Check if last row has right number of columns
        const last_row = rows[rows.length - 1];
        if ((last_row.children.length % 2) != (numBoxes % 2)) {
            if (numBoxes % 2 == 1) {
                const last_box = last_row.children[last_row.children.length - 1];
                last_row.removeChild(last_box);
            } else {
                last_row.appendChild(constructBox(numBoxes - 1));
            }
        }
    }
}

function updateJob(jobId, newData) {
    const boxNum = job_to_box.get(jobId);
    const boxData = boxMap.get(boxNum);
    // change button to reflect the abort acknowledged
    if (newData.abort_ack) abortAcknowledged(boxData.abortButton);
    if (boxData.header.innerText=="") {
        boxData.header.innerText = newData.model_name;
    }
    console.log(Object.keys(newData.progress));
    const max_epoch = Math.max(...Array.from(Object.keys(newData.progress)).map(x => parseInt(x)));
    if (max_epoch >= 0) {
        updateLogs(boxNum, newData.logs);
        updateDatasets(boxData.chart, jobId, newData.progress, max_epoch);
        console.log(boxNum, newData.progress[max_epoch], max_epoch);
        updateProgress(boxNum, newData.progress[max_epoch], max_epoch);
    }
}

socket.onmessage = function(e) {
    console.log(e);
    var eventData = JSON.parse(e.data).all_data;
    var active_jobs = Array.from(Object.keys(eventData)).map(x => parseInt(x));
    var r = rejigBoxes(active_jobs);
    var boxes_to_load = r.boxes_to_load;
    resizeGrid(active_jobs.length);
    for (const i of boxes_to_load) {
        reconstructBox(i);
    }
    for (const job_id of active_jobs) {
        updateJob(job_id, eventData[job_id.toString()]);
    }
}

function logObjectToP(logObject, boxNum) {
    var timeElem = document.createElement(null);
    timeElem.className = "logTime".concat(boxNum.toString())
    timeElem.innerText = logObject.time + " ";
    var orderElem = document.createElement(null);
    orderElem.innerText = logObject.order + " ";
    timeElem.className = "logOrder".concat(boxNum.toString())
    var message = logObject.message;
    var p = document.createElement("p");
    var loglevelstr = loglevel_to_name.get(logObject.log_level);
    p.className += loglevelstr.concat(boxNum.toString())
    var messageElem = document.createElement(null);
    messageElem.innerText = message;
    p.appendChild(orderElem);
    p.appendChild(timeElem);
    p.appendChild(messageElem);
    return p;
}

function updateLogs(boxNum, newLogs) {
    var logboxElement = boxMap.get(boxNum).logbox.logboxElement;
    for (const logObject of newLogs) {
        logboxElement.appendChild(logObjectToP(logObject, boxNum));
        logboxElement.scrollTop = logboxElement.scrollHeight;
    }
}

function updateDatasets(chart, job_id, newData, maxEpoch) {
    // check for new series
    const job_data = jobMap.get(job_id);
    // extend labels with new values
    const current_max_epoch = job_data.get("max_epoch");
    const labels = job_data.get("labels");
    for (const i of range(current_max_epoch, maxEpoch + 1, 1)) {
        labels.push(i);
    }
    // extend datasets with null values
    const current_dataset = job_data.get("datasets");
    for (const [series_name, series_data] of current_dataset.entries()) {
        for (const i of range(current_max_epoch, maxEpoch + 1, 1)) {
            series_data.push(null);
        }
    }
    for (const epoch of Object.keys(newData)) {
        for (const series_name of Object.keys(newData[epoch])) {
            if (!current_dataset.has(series_name)) {
                console.log(maxEpoch);
                const new_series_data = Array(maxEpoch + 1).fill(null);
                // construct new dataset item and add it to the chart
                // TODO: This only supports 3 series! NOT GOOD!
                const num_series = current_dataset.size;
                const new_colour = chart_colours[num_series];
                const new_chart_dataset = {
                        label: series_name.concat(" loss"),
                        data: new_series_data,
                        borderColor: new_colour,
                        cubicInterpolationMode: 'monotone',
                        tension: 0.4
                    }
                chart.data.datasets.push(new_chart_dataset);
                current_dataset.set(series_name, new_series_data);
            }
            current_dataset.get(series_name)[parseInt(epoch)] = newData[epoch][series_name].loss;
        }
    }
    // interpolate
    for (const series_data of current_dataset.values()) {
        interpolate(series_data, 0);
    }
    // update datasets for job
    job_data.set("max_epoch", maxEpoch)
    chart.update();
}

function updateProgress(boxNum, progress, epoch) {
    const progressBarElement = boxMap.get(boxNum).bar
    // TODO: Simply selecting the first series is a really bad idea and needs to be improved upon
    console.log(boxNum, progress);
    //console.log(progress);
    const series = progress[Object.keys(progress)[0]];
    const series_progess = Math.round(series.progress * 100);
    setProgress(progressBarElement, series_progess, "Epoch " + epoch + ": "+ series_progess + "%");
}

function setProgress(progressbar, progress, text) {
    progressbar.style.width = progress + "%";
    progressbar.setAttribute("aria-valuenow", '"' + progress + '"');
    progressbar.innerHTML = text;
}

function interpolate(arr, initial_val) {
    if (arr[0] == null) {arr[0] = initial_val;}
    var last_valid = 0;
    for (var i = 1; i < arr.length; i++) {
        if (arr[i] != null) {
            if (i > (last_valid + 1)) {
                // interpolate
                const delta = (arr[i] - arr[last_valid]) / (i - last_valid)
                for (var j = last_valid + 1; j < i; j ++) {
                    arr[j] = arr[j - 1] + delta;
                }
            }
            last_valid = i;
        }
    }
}

window.addEventListener("load", function(){
    head = document.getElementsByTagName('head')[0];
});