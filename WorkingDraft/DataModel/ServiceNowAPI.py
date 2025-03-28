from pydantic import BaseModel
from typing import List, Optional

class Task(BaseModel):
    parent: Optional[str]
    made_sla: str
    watch_list: Optional[str]
    sc_catalog: Optional[str]
    upon_reject: str
    sn_esign_document: Optional[str]
    sys_updated_on: str
    x_htapt_tensai_sub_status_tsm: Optional[str]
    task_effective_number: str
    approval_history: Optional[str]
    skills: Optional[str]
    number: str
    sys_updated_by: str
    user_input: Optional[str]
    opened_by: str
    sys_created_on: str
    sys_domain: str
    state: str
    sys_created_by: str
    route_reason: Optional[str]
    knowledge: str
    order: Optional[str]
    calendar_stc: Optional[str]
    closed_at: Optional[str]
    delivery_plan: Optional[str]
    cmdb_ci: Optional[str]
    impact: str
    contract: Optional[str]
    active: str
    work_notes_list: Optional[str]
    sn_hr_le_activity: Optional[str]
    business_service: Optional[str]
    priority: str
    sys_domain_path: str
    time_worked: Optional[str]
    rejection_goto: Optional[str]
    expected_start: Optional[str]
    opened_at: str
    group_list: Optional[str]
    business_duration: Optional[str]
    work_end: Optional[str]
    approval_set: Optional[str]
    wf_activity: Optional[str]
    work_notes: Optional[str]
    universal_request: Optional[str]
    request: Optional[str]
    short_description: str
    correlation_display: Optional[str]
    delivery_task: Optional[str]
    work_start: str
    assignment_group: str
    additional_assignee_list: Optional[str]
    description: Optional[str]
    calendar_duration: Optional[str]
    service_offering: Optional[str]
    sys_class_name: str
    close_notes: Optional[str]
    follow_up: Optional[str]
    closed_by: Optional[str]
    sn_esign_esignature_configuration: Optional[str]
    contact_type: Optional[str]
    urgency: str
    company: Optional[str]
    reassignment_count: str
    activity_due: Optional[str]
    assigned_to: Optional[str]
    variables: Optional[str]
    comments: Optional[str]
    approval: str
    sla_due: Optional[str]
    comments_and_work_notes: Optional[str]
    due_date: Optional[str]
    sys_mod_count: str
    request_item: Optional[str]
    sys_tags: Optional[str]
    cat_item: Optional[str]
    escalation: str
    upon_approval: str
    correlation_id: Optional[str]
    location: Optional[str]

class APIResponse(BaseModel):
    result: List[Task]
