function rejigBoxes(active_job_ids) {
    var free_boxes = [];
    var occupied_boxes = [];
    // check if any jobs have become inactive
    for (const [key, value] of job_to_box.entries()) {
        if (!active_job_ids.includes(key)){
            console.log(key);
            free_boxes.push(value);
            box_to_job.set(value, null);
            job_to_box.set(key, null);
            elemMap.delete(key);
        } else {
            occupied_boxes.push(value);
        }
    }
    var new_jobs = []
    // check for new jobs
    for (const job_id of active_job_ids) {
        if (!job_to_box.has(job_id)) {
            new_jobs.push(job_id);
        }
    }
    // iterate over free boxes, assigning them to jobs
    while ((free_boxes.length > 0) && (new_jobs.length > 0)) {
        free_box = free_boxes.pop();
        new_job = new_jobs.pop()
        job_to_box.set(new_job, free_box);
        box_to_job.set(free_box, new_job);
        occupied_boxes.push(free_box);
    }
    free_boxes.sort();
    occupied_boxes.sort();
    // check what remains
    var redraw = [];
    var remove = [];
    if (free_boxes.length > 0) {
        // need to do some shifting/rejigging
        // rejigging means moving only the boxes which need to be moved
        // assuming the constraint that there shouldn't be any empty boxes at the end
        var i = 0;
        while (i < occupied_boxes.length) {
            if (occupied_boxes[i] < free_boxes[0]) {
                i += 1;
            } else {
                const destination_box = free_boxes[0];
                free_boxes[0] = occupied_boxes[i];
                redraw.push(destination_box);
                free_boxes.sort(); // need a more efficient algorithm
                job_id = box_to_job.get(occupied_boxes[i]);
                occupied_boxes[i] = destination_box;
                job_to_box.set(job_id, destination_box);
                box_to_job.set(destination_box, job_id);
            }

        }
        remove = free_boxes;
        box_count = occupied_boxes.length;
    } else if (new_jobs.length > 0) {
        // need new boxes
        for (const i of range(0, new_jobs.length, 1)) {
          box_to_job.set(box_count + i, new_jobs[i]);
        }
        box_count = new_jobs.length;
    }
    return [redraw, remove];
}