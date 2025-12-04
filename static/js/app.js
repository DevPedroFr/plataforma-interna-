// Navigation
const navLinks = document.querySelectorAll('.nav-link');
const pages = document.querySelectorAll('.page');

navLinks.forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        
        // Remove active from all
        navLinks.forEach(l => l.classList.remove('active'));
        pages.forEach(p => p.classList.remove('active'));
        
        // Add active to clicked
        link.classList.add('active');
        const pageId = link.getAttribute('data-page');
        document.getElementById(pageId).classList.add('active');
    });
});

// Charts - Dashboard
if (document.getElementById('stockChart')) {
    const stockCtx = document.getElementById('stockChart').getContext('2d');
    const stockChart = new Chart(stockCtx, {
        type: 'bar',
        data: {
            labels: ['COVID-19', 'Influenza', 'Hepatite B', 'Tétano', 'Febre Amarela'],
            datasets: [{
                label: 'Estoque Atual',
                data: [150, 200, 80, 120, 90],
                backgroundColor: 'rgba(59, 130, 246, 0.8)',
                borderColor: 'rgb(59, 130, 246)',
                borderWidth: 1
            }, {
                label: 'Estoque Mínimo',
                data: [50, 80, 40, 60, 45],
                backgroundColor: 'rgba(239, 68, 68, 0.8)',
                borderColor: 'rgb(239, 68, 68)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

if (document.getElementById('chatbotChart')) {
    const chatbotCtx = document.getElementById('chatbotChart').getContext('2d');
    const chatbotChart = new Chart(chatbotCtx, {
        type: 'line',
        data: {
            labels: ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'],
            datasets: [{
                label: 'Agendamentos',
                data: [45, 52, 38, 61, 49, 28, 15],
                borderColor: 'rgb(139, 92, 246)',
                backgroundColor: 'rgba(139, 92, 246, 0.1)',
                tension: 0.4,
                fill: true
            }, {
                label: 'Consultas',
                data: [38, 48, 35, 55, 44, 25, 13],
                borderColor: 'rgb(16, 185, 129)',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                tension: 0.4,
                fill: true
            }, {
                label: 'Atendimento Humano',
                data: [7, 4, 3, 6, 5, 3, 2],
                borderColor: 'rgb(245, 158, 11)',
                backgroundColor: 'rgba(245, 158, 11, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// WhatsApp conversation switching
const conversationItems = document.querySelectorAll('.conversation-item');
conversationItems.forEach(item => {
    item.addEventListener('click', () => {
        conversationItems.forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        
        // Aqui você pode carregar a conversa específica
        const userName = item.querySelector('strong').textContent;
        document.querySelector('.chat-header h3').textContent = userName;
    });
});
