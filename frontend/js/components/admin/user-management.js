/**
 * User Management Component for MAMcrawler Admin Panel
 * Handles user CRUD operations and role management
 */

class UserManagement {
    constructor() {
        this.users = [];
        this.currentUser = null;
        this.init();
    }

    /**
     * Initialize user management
     */
    init() {
        this.bindEvents();
    }

    /**
     * Bind event listeners
     */
    bindEvents() {
        // Add user button
        const addUserBtn = document.getElementById('add-user-btn');
        if (addUserBtn) {
            addUserBtn.addEventListener('click', () => this.showUserModal());
        }

        // User form
        const userForm = document.getElementById('user-form');
        if (userForm) {
            userForm.addEventListener('submit', (e) => this.handleUserSubmit(e));
        }
    }

    /**
     * Load users list
     */
    async loadUsers() {
        try {
            const response = await window.authService.apiCall('/admin/users');
            if (response.success) {
                this.users = response.data.users || [];
                this.renderUsersTable();
            } else {
                window.adminPanel.showToast('Failed to load users', 'error');
            }
        } catch (error) {
            console.error('Failed to load users:', error);
            window.adminPanel.showToast('Failed to load users', 'error');
        }
    }

    /**
     * Render users table
     */
    renderUsersTable() {
        const tbody = document.getElementById('users-table-body');
        if (!tbody) return;

        if (this.users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="loading">No users found</td></tr>';
            return;
        }

        tbody.innerHTML = this.users.map(user => `
            <tr>
                <td>${this.escapeHtml(user.username)}</td>
                <td>${this.escapeHtml(user.email)}</td>
                <td><span class="role-badge role-${user.role}">${user.role}</span></td>
                <td><span class="status-badge status-${user.is_active ? 'active' : 'inactive'}">${user.is_active ? 'Active' : 'Inactive'}</span></td>
                <td>${user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}</td>
                <td>
                    <button class="btn btn-secondary btn-sm" onclick="window.userManagement.editUser(${user.id})">Edit</button>
                    <button class="btn btn-danger btn-sm" onclick="window.userManagement.deleteUser(${user.id})">Delete</button>
                </td>
            </tr>
        `).join('');
    }

    /**
     * Show user modal
     */
    showUserModal(user = null) {
        this.currentUser = user;
        const modal = document.getElementById('user-modal');
        const form = document.getElementById('user-form');
        const title = document.getElementById('user-modal-title');

        if (user) {
            title.textContent = 'Edit User';
            this.populateUserForm(user);
        } else {
            title.textContent = 'Add New User';
            form.reset();
            document.getElementById('user-id').value = '';
        }

        modal.style.display = 'flex';
    }

    /**
     * Populate user form
     */
    populateUserForm(user) {
        document.getElementById('user-id').value = user.id || '';
        document.getElementById('user-username').value = user.username || '';
        document.getElementById('user-email').value = user.email || '';
        document.getElementById('user-password').value = ''; // Don't populate password
        document.getElementById('user-role').value = user.role || 'viewer';
        document.getElementById('user-active').checked = user.is_active !== false;
    }

    /**
     * Handle user form submission
     */
    async handleUserSubmit(event) {
        event.preventDefault();

        const formData = new FormData(event.target);
        const userData = {
            id: formData.get('id') || null,
            username: formData.get('username'),
            email: formData.get('email'),
            password: formData.get('password'),
            role: formData.get('role'),
            is_active: formData.get('is_active') === 'on'
        };

        // Validate user data
        if (!this.validateUserData(userData)) {
            return;
        }

        const isEdit = !!userData.id;
        const url = isEdit ? `/admin/users/${userData.id}` : '/admin/users';
        const method = isEdit ? 'PUT' : 'POST';

        // Remove empty password for edits
        if (isEdit && !userData.password) {
            delete userData.password;
        }

        try {
            window.adminPanel.showLoading(true);
            const response = await window.authService.apiCall(url, {
                method,
                body: JSON.stringify(userData)
            });

            if (response.success) {
                window.adminPanel.hideModals();
                await this.loadUsers();
                window.adminPanel.showToast(`User ${isEdit ? 'updated' : 'created'} successfully`, 'success');
            } else {
                window.adminPanel.showToast(response.error || 'Failed to save user', 'error');
            }
        } catch (error) {
            console.error('User save error:', error);
            window.adminPanel.showToast('Failed to save user', 'error');
        } finally {
            window.adminPanel.showLoading(false);
        }
    }

    /**
     * Edit user
     */
    async editUser(userId) {
        const user = this.users.find(u => u.id === userId);
        if (user) {
            this.showUserModal(user);
        } else {
            // Load user details if not in current list
            try {
                const response = await window.authService.apiCall(`/admin/users/${userId}`);
                if (response.success) {
                    this.showUserModal(response.data.user);
                }
            } catch (error) {
                console.error('Failed to load user:', error);
                window.adminPanel.showToast('Failed to load user', 'error');
            }
        }
    }

    /**
     * Delete user
     */
    async deleteUser(userId) {
        const user = this.users.find(u => u.id === userId);
        const username = user ? user.username : 'user';

        if (!confirm(`Are you sure you want to delete user "${username}"? This action cannot be undone.`)) {
            return;
        }

        try {
            window.adminPanel.showLoading(true);
            const response = await window.authService.apiCall(`/admin/users/${userId}`, {
                method: 'DELETE'
            });

            if (response.success) {
                await this.loadUsers();
                window.adminPanel.showToast('User deleted successfully', 'success');
            } else {
                window.adminPanel.showToast(response.error || 'Failed to delete user', 'error');
            }
        } catch (error) {
            console.error('User delete error:', error);
            window.adminPanel.showToast('Failed to delete user', 'error');
        } finally {
            window.adminPanel.showLoading(false);
        }
    }

    /**
     * Validate user data
     */
    validateUserData(userData) {
        const errors = [];

        // Username validation
        if (!userData.username || userData.username.length < 3) {
            errors.push('Username must be at least 3 characters long');
        }

        if (!/^[a-zA-Z0-9_-]+$/.test(userData.username)) {
            errors.push('Username can only contain letters, numbers, underscores, and hyphens');
        }

        // Check for duplicate username
        const existingUser = this.users.find(u =>
            u.username === userData.username && u.id !== userData.id
        );
        if (existingUser) {
            errors.push('Username already exists');
        }

        // Email validation
        if (!userData.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(userData.email)) {
            errors.push('Please enter a valid email address');
        }

        // Check for duplicate email
        const existingEmail = this.users.find(u =>
            u.email === userData.email && u.id !== userData.id
        );
        if (existingEmail) {
            errors.push('Email address already exists');
        }

        // Password validation (only for new users or when changing password)
        if (!userData.id || userData.password) {
            if (!userData.password || userData.password.length < 8) {
                errors.push('Password must be at least 8 characters long');
            }
        }

        // Role validation
        const validRoles = ['viewer', 'moderator', 'admin'];
        if (!validRoles.includes(userData.role)) {
            errors.push('Please select a valid role');
        }

        if (errors.length > 0) {
            errors.forEach(error => window.adminPanel.showToast(error, 'error'));
            return false;
        }

        return true;
    }

    /**
     * Export users list
     */
    exportUsers() {
        const csvContent = [
            ['Username', 'Email', 'Role', 'Status', 'Last Login', 'Created'],
            ...this.users.map(user => [
                user.username,
                user.email,
                user.role,
                user.is_active ? 'Active' : 'Inactive',
                user.last_login || 'Never',
                user.created_at || 'Unknown'
            ])
        ].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `mamcrawler-users-${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        window.adminPanel.showToast('Users exported successfully', 'success');
    }

    /**
     * Bulk user operations
     */
    async bulkActivateUsers(userIds, activate = true) {
        try {
            const response = await window.authService.apiCall('/admin/users/bulk/status', {
                method: 'PUT',
                body: JSON.stringify({ user_ids: userIds, is_active: activate })
            });

            if (response.success) {
                await this.loadUsers();
                window.adminPanel.showToast(`Users ${activate ? 'activated' : 'deactivated'} successfully`, 'success');
            } else {
                window.adminPanel.showToast(response.error || 'Bulk operation failed', 'error');
            }
        } catch (error) {
            console.error('Bulk operation error:', error);
            window.adminPanel.showToast('Bulk operation failed', 'error');
        }
    }

    /**
     * Get user statistics
     */
    getUserStats() {
        const stats = {
            total: this.users.length,
            active: this.users.filter(u => u.is_active).length,
            inactive: this.users.filter(u => !u.is_active).length,
            admins: this.users.filter(u => u.role === 'admin').length,
            moderators: this.users.filter(u => u.role === 'moderator').length,
            viewers: this.users.filter(u => u.role === 'viewer').length
        };

        return stats;
    }

    /**
     * Escape HTML for security
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Create global instance
window.userManagement = new UserManagement();

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UserManagement;
}