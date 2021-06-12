from django.shortcuts import get_object_or_404
from .forms import ProjectCreateFormRoot, ProjectCreateFormChild, MLModelCreateForm
from .models import Project, MLModel
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, DetailView, ListView, UpdateView, DeleteView

class AuthMixin(LoginRequiredMixin):
    @property
    def queryset(self):
        viewable_projects = Project.objects.filter(auth_users__id=self.request.user.id)
        return viewable_projects

class AdminMixin(LoginRequiredMixin):
    @property
    def queryset(self):
        viewable_projects = Project.objects.filter(auth_users__id=self.request.user.id)
        # need to also check if user is correct type
        return viewable_projects

class ProjectListView(AuthMixin, ListView):
    template_name = 'project_list.html'

    @property
    def queryset(self):
        viewable_projects = Project.objects.filter(auth_users__id=self.request.user.id, parent=None)
        return viewable_projects

class ProjectDetailView(AuthMixin, DetailView):
    template_name = 'project_detail.html'
        
    def children(self):
        id_ = self.kwargs.get("id")
        obj = Project.objects.get(id=id_)
        viewable_projects = Project.objects.filter(auth_users__id=self.request.user.id, parent=obj)
        viewable_mlmodels = MLModel.objects.filter(auth_users__id=self.request.user.id, parent=obj)
        # print(viewable_projects, viewable_mlmodels)
        return viewable_projects, viewable_mlmodels

    def get_object(self):
        id_ = self.kwargs.get("id")
        return get_object_or_404(Project, id=id_)

    def get_context_data(self, **kwargs):
        # print(self.object.get_create_url())
        context = super().get_context_data(**kwargs)
        context['subprojects'], context['mlmodels'] = self.children()
        # print(context)
        return context

class ProjectDeleteView(AdminMixin, DeleteView):
    template_name = 'project_delete.html'
    
    def get_object(self):
        id_ = self.kwargs.get("id")
        # need to also check if user is correct type
        obj = get_object_or_404(Project, id=id_)
        self.parent = self.obj.parent
        return obj

    def get_success_url(self):
        if self.parent is None:
            return reverse("projects:project-list")
        else:
            return self.parent.get_absolute_url()

class SubprojectMixin():
    form_class = ProjectCreateFormChild

class RootProjectMixin():
    form_class = ProjectCreateFormRoot

class ModifMixin():
    template_name = 'project_create.html'
    
    def form_valid(self, form):
        candidate = form.save(commit=False)
        candidate.save()
        self.id = candidate.id
        candidate.auth_users.add(self.request.user)
        return super().form_valid(form)

class ProjectCreateView(ModifMixin, AuthMixin, CreateView):   
    def form_valid(self, form):
        candidate = form.save(commit=False)
        while candidate.path[-1] == "/":
            candidate.path = candidate.path[:-1]
        candidate.parent = self.parent
        candidate.save()
        self.id = candidate.id
        candidate.auth_users.add(self.request.user)
        return CreateView.form_valid(self, form)

class ProjectCreateViewChild(SubprojectMixin, ProjectCreateView):
    def form_valid(self, form):
        candidate = form.save(commit=False)
        candidate.parent = self.parent        
        candidate.path = None
        candidate.save()
        candidate.auth_users.add(self.request.user)
        return CreateView.form_valid(self, form)

    def get_form(self, *args, **kwargs):
        # print("************" + str(self.request.path.split("/")[-2]))
        parent_id = self.request.path.split("/")[-2]
        # print(parent_id)
        self.parent = Project.objects.get(id=parent_id)
        form = super().get_form(*args, **kwargs)
        form.parent = self.parent
        form.fq_path = self.parent.get_fq_path

        return form

class ProjectCreateViewRoot(RootProjectMixin, ProjectCreateView):
    def get_form(self, *args, **kwargs):
        self.parent = None
        form = super().get_form(*args, **kwargs)
        return form

class ProjectUpdateView(ModifMixin, AdminMixin, UpdateView):
    pass

class MLModelDetailView(LoginRequiredMixin, DetailView):
    template_name = 'mlmodel_detail.html'

    def get_object(self):
        id_ = self.kwargs.get("id")
        obj = get_object_or_404(MLModel, id=id_)
        # print(obj)
        # print(obj.get_ancestors)
        return obj

class MLModelDeleteView(LoginRequiredMixin, DeleteView):
    template_name = 'mlmodel_delete.html'
    
    def get_object(self):
        id_ = self.kwargs.get("id")
        # need to also check if user is correct type
        obj = get_object_or_404(MLModel, id=id_)
        # print(obj)
        self.parent = self.obj.parent
        return obj

    def get_success_url(self):
        return self.parent.get_absolute_url()

class MLModelCreateView(LoginRequiredMixin, CreateView):
    template_name = 'mlmodel_create.html'
    form_class = MLModelCreateForm

    def form_valid(self, form):
        candidate = form.save(commit=False)
        candidate.parent = self.parent        
        candidate.save()
        candidate.auth_users.add(self.request.user)
        return CreateView.form_valid(self, form)

    def get_form(self, *args, **kwargs):
        parent_id = self.request.path.split("/")[-2]
        # (parent_id)
        self.parent = Project.objects.get(id=parent_id)
        form = super().get_form(*args, **kwargs)
        form.parent = self.parent
        form.fq_path = self.parent.get_fq_path
        return form