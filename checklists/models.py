from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    ROLES = [
        ('ADMIN', 'Admin'),
        ('GESTOR', 'Gestor'),
        ('CONTROLADOR', 'Controlador de Acesso'),
        ('MANUTENCAO', 'Manutenção'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLES, default='CONTROLADOR')
    cpf = models.CharField(max_length=14, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"

class Condutor(models.Model):
    nome = models.CharField(max_length=100)
    cpf = models.CharField(max_length=14, unique=True)
    data_nascimento = models.DateField(blank=True, null=True)

    class Meta:
        verbose_name = "Motorista/Condutor"
        verbose_name_plural = "Motoristas/Condutores"

    def __str__(self):
        return f"{self.nome} ({self.cpf})"

class Veiculo(models.Model):
    TIPO_CHOICES = [
        ('CAVALO', 'Cavalo Mecânico'),
        ('CARRETA', 'Carreta'),
    ]
    placa = models.CharField(max_length=10, unique=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    id_frota = models.CharField(max_length=50, blank=True, null=True)
    marca = models.CharField(max_length=50, blank=True, null=True)
    modelo = models.CharField(max_length=50, blank=True, null=True)
    ano_fabricacao = models.IntegerField(blank=True, null=True)
    ano_modelo = models.IntegerField(blank=True, null=True)

    class Meta:
        verbose_name = "Veículo"
        verbose_name_plural = "Veículos"

    def __str__(self):
        return f"{self.placa} ({self.get_tipo_display()})"

class Checklist(models.Model):
    EQUIPMENT_CHOICES = [
        ('PRANCHA', 'Prancha'),
        ('TAMPA', 'Com Tampa'),
        ('BUGRE_20', "Bugre 20'"),
        ('BITREM', 'Bitrem'),
    ]

    STATUS_CHOICES = [
        ('SIM', 'Sim'),
        ('NAO', 'Não'),
        ('NA', 'N/A'),
    ]

    placa_cavalo = models.ForeignKey(Veiculo, on_delete=models.PROTECT, related_name='checklists_cavalo', limit_choices_to={'tipo': 'CAVALO'})
    nome_motorista = models.ForeignKey(Condutor, on_delete=models.PROTECT, related_name='checklists')
    placa_carreta_01 = models.ForeignKey(Veiculo, on_delete=models.SET_NULL, related_name='checklists_carreta1', blank=True, null=True, limit_choices_to={'tipo': 'CARRETA'})
    placa_carreta_02 = models.ForeignKey(Veiculo, on_delete=models.SET_NULL, related_name='checklists_carreta2', blank=True, null=True, limit_choices_to={'tipo': 'CARRETA'})
    doc_carreta_entregue = models.BooleanField(default=False)
    tipo_equipamento = models.CharField(max_length=20, choices=EQUIPMENT_CHOICES, default='PRANCHA')
    
    # Parte Eletrica
    eletrica_condicoes = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    eletrica_seta = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    eletrica_re = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    eletrica_freio = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    eletrica_capas = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    eletrica_placa = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')

    # Sistema Mecanico
    mecanica_freios = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    mecanica_conexoes = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    mecanica_folga_quinta_roda = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    mecanica_suspensao = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    mecanica_freio_estacionario = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    mecanica_travas_conteiner = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    mecanica_tampas_equipamento = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    mecanica_tampas_estado = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')

    # Rodas e Pneus
    rodas_pneus_quantidade = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    rodas_pneus_reserva = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    rodas_pneus_estado = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    rodas_pneus_cortes_bolhas = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')

    anomalias = models.TextField(blank=True, null=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    porteiro = models.ForeignKey(User, on_delete=models.CASCADE, related_name='checklists')
    tempo_execucao = models.PositiveIntegerField(null=True, blank=True)

    @property
    def tempo_formatado(self):
        if self.tempo_execucao is None:
            return "--:--"
        minutes = self.tempo_execucao // 60
        seconds = self.tempo_execucao % 60
        return f"{minutes:02d}:{seconds:02d}"

    # Assinaturas e fluxos
    visto_responsavel_saida = models.TextField(blank=True, null=True)
    visto_motorista_saida = models.TextField(blank=True, null=True)

    data_hora_devolucao = models.DateTimeField(blank=True, null=True)
    visto_responsavel_devolucao = models.TextField(blank=True, null=True)
    visto_motorista_devolucao = models.TextField(blank=True, null=True)

    # Resolução de NC
    resolvido_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_portaria')
    data_resolucao = models.DateTimeField(null=True, blank=True)

    @property
    def has_nc(self):
        # Check anomalias text
        if self.anomalias and self.anomalias.strip():
            return True
        # Check condition fields
        fields = [
            'eletrica_condicoes', 'eletrica_seta', 'eletrica_re', 'eletrica_freio', 'eletrica_capas', 'eletrica_placa',
            'mecanica_freios', 'mecanica_conexoes', 'mecanica_folga_quinta_roda', 'mecanica_suspensao', 
            'mecanica_freio_estacionario', 'mecanica_travas_conteiner', 'mecanica_tampas_equipamento', 'mecanica_tampas_estado',
            'rodas_pneus_quantidade', 'rodas_pneus_reserva', 'rodas_pneus_estado', 'rodas_pneus_cortes_bolhas'
        ]
        for f in fields:
            if getattr(self, f) == 'NAO':
                return True
        return False

    @property
    def is_resolved(self):
        return self.resolvido_por is not None

    class Meta:
        verbose_name = "Checklist de Portaria"
        verbose_name_plural = "Checklists de Portaria"

    def __str__(self):
        return f"Checklist {self.placa_cavalo} - {self.data_criacao.strftime('%d/%m/%Y %H:%M')}"

class AlertEmail(models.Model):
    CATEGORIES = [
        ('PORTARIA', 'Portaria / Controlador de Acesso'),
        ('MANUTENCAO', 'Manutenção'),
        ('AGENDA', 'Agenda de Manutenção'),
    ]
    email = models.EmailField()
    category = models.CharField(max_length=20, choices=CATEGORIES, default='PORTARIA')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Alerta de E-mail"
        verbose_name_plural = "Alertas de E-mail"
        unique_together = ('email', 'category')

    def __str__(self):
        return f"{self.email} ({self.get_category_display()})"

class MaintenanceTruck(models.Model):
    STATUS_CHOICES = [
        ('SIM', 'Sim'),
        ('NAO', 'Não'),
        ('NA', 'N/A'),
    ]
    
    veiculo = models.ForeignKey(Veiculo, on_delete=models.PROTECT, limit_choices_to={'tipo': 'CAVALO'})
    motorista = models.ForeignKey(Condutor, on_delete=models.PROTECT)
    data_criacao = models.DateTimeField(auto_now_add=True)
    responsavel = models.ForeignKey(User, on_delete=models.CASCADE)
    quilometragem = models.CharField(max_length=20, blank=True, null=True)
    
    # Itens (29)
    cinto_seguranca = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    pneus_estado = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    rodas_estado = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    freio_perfeito = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    freio_estacionamento = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    direcao_estado = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    limpador_parabrisa = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    instrumentos_painel = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    retrovisor_estado = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    buzina_funcionando = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    farol_funcionando = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    setas_funcionando = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    alerta_funcionando = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    luz_alarme_re = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    luz_freio = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    extintor_vencimento = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    oleo_hidraulico = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    oleo_freio = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    oleo_motor = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    correias_estado = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    agua_radiador = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    bateria_estado = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    escapamento_estado = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    tampa_combustivel = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    macaco_hidraulico = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    bancos_limpeza = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    chave_triangulo = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    tacografo_disco = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    carroceria_estado = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    tempo_execucao = models.PositiveIntegerField(null=True, blank=True)

    @property
    def tempo_formatado(self):
        if self.tempo_execucao is None:
            return "--:--"
        minutes = self.tempo_execucao // 60
        seconds = self.tempo_execucao % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    observacoes = models.TextField(blank=True, null=True)
    visto_responsavel = models.TextField(blank=True, null=True)
    visto_motorista = models.TextField(blank=True, null=True)

    # Resolução de NC
    resolvido_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_trucks')
    data_resolucao = models.DateTimeField(null=True, blank=True)

    @property
    def has_nc(self):
        if self.observacoes and self.observacoes.strip():
            return True
        from .constants import TRUCK_MAINTENANCE_ITEMS
        for item in TRUCK_MAINTENANCE_ITEMS:
            if getattr(self, item['id']) == 'NAO':
                return True
        return False

    @property
    def is_resolved(self):
        return self.resolvido_por is not None

    class Meta:
        verbose_name = "Manutenção de Caminhão"
        verbose_name_plural = "Manutenções de Caminhão"

    def __str__(self):
        return f"MNT Caminhão {self.veiculo.placa} - {self.data_criacao.strftime('%d/%m/%y')}"

class MaintenanceTrailer(models.Model):
    STATUS_CHOICES = [
        ('SIM', 'Sim'),
        ('NAO', 'Não'),
        ('NA', 'N/A'),
    ]
    
    veiculo = models.ForeignKey(Veiculo, on_delete=models.PROTECT, limit_choices_to={'tipo': 'CARRETA'})
    motorista = models.ForeignKey(Condutor, on_delete=models.PROTECT)
    data_criacao = models.DateTimeField(auto_now_add=True)
    responsavel = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Itens (31)
    perfil_dianteiro = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    perfil_traseiro = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    perfil_lateral_dir = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    perfil_lateral_esq = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    freio_estacionamento = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    alinhamento_eixos = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    parachoques = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    aparabarros = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    paralamas = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    pes_carreta = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    suspensor_1eixo = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    suspensor_2eixo = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    alerta = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    setas = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    luz_freio = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    luz_re = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    luz_placa = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    lentes_laterais = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    pino_rei = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    sistema_pneumatico = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    engate_eletrico = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    engates_pneumaticos = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    tampas_lat_dir = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    tampas_lat_esq = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    tampa_traseira = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    tampa_dianteira = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    pinos_locke = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    faixas_refletivas = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    faixa_parachoques = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    suporte_estepe = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    suspensao_geral = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    tempo_execucao = models.PositiveIntegerField(null=True, blank=True)

    @property
    def tempo_formatado(self):
        if self.tempo_execucao is None:
            return "--:--"
        minutes = self.tempo_execucao // 60
        seconds = self.tempo_execucao % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    visto_responsavel = models.TextField(blank=True, null=True)
    visto_motorista = models.TextField(blank=True, null=True)

    # Resolução de NC
    resolvido_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_trailers')
    data_resolucao = models.DateTimeField(null=True, blank=True)

    @property
    def has_nc(self):
        if self.observacoes and self.observacoes.strip():
            return True
        from .constants import TRAILER_MAINTENANCE_ITEMS
        for item in TRAILER_MAINTENANCE_ITEMS:
            if getattr(self, item['id']) == 'NAO':
                return True
        return False

    @property
    def is_resolved(self):
        return self.resolvido_por is not None

    class Meta:
        verbose_name = "Manutenção de Carreta"
        verbose_name_plural = "Manutenções de Carreta"

    def __str__(self):
        return f"MNT Carreta {self.veiculo.placa} - {self.data_criacao.strftime('%d/%m/%y')}"

class ChecklistForklift(models.Model):
    EQUIPMENT_TYPES = [
        ('MILA', 'MILA'),
        ('ASA_DELTA', 'ASA DELTA'),
        ('HYSTER', 'HYSTER DE 7 TON'),
    ]
    STATUS_CHOICES = [
        ('SIM', 'Sim'),
        ('NAO', 'Não'),
        ('NA', 'N/A'),
    ]
    
    operador = models.ForeignKey(Condutor, on_delete=models.PROTECT, related_name='forklift_checklists')
    tipo_equipamento = models.CharField(max_length=20, choices=EQUIPMENT_TYPES)
    data_criacao = models.DateTimeField(auto_now_add=True)
    responsavel = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forklift_checklists')
    
    # Itens (10)
    mangueiras = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    pneus = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    pistao_elevacao = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    pistao_inclinacao = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    direcao = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    cabo_aco = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    parte_eletrica = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    corrente_torre = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    vazamento_oleo = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    pintura = models.CharField(max_length=3, choices=STATUS_CHOICES, default='NA')
    tempo_execucao = models.PositiveIntegerField(null=True, blank=True)

    @property
    def tempo_formatado(self):
        if self.tempo_execucao is None:
            return "--:--"
        minutes = self.tempo_execucao // 60
        seconds = self.tempo_execucao % 60
        return f"{minutes:02d}:{seconds:02d}"

    observacoes = models.TextField(blank=True, null=True)
    visto_responsavel = models.TextField(blank=True, null=True)
    visto_operador = models.TextField(blank=True, null=True)

    # Resolução de NC
    resolvido_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_forklifts')
    data_resolucao = models.DateTimeField(null=True, blank=True)

    @property
    def has_nc(self):
        if self.observacoes and self.observacoes.strip():
            return True
        from .constants import FORKLIFT_ITEMS
        for item in FORKLIFT_ITEMS:
            if getattr(self, item['id']) == 'NAO':
                return True
        return False

    @property
    def is_resolved(self):
        return self.resolvido_por is not None

    class Meta:
        verbose_name = "Checklist de Empilhadeira"
        verbose_name_plural = "Checklists de Empilhadeira"

    def __str__(self):
        return f"Checklist Empilhadeira {self.tipo_equipamento} - {self.data_criacao.strftime('%d/%m/%y')}"

class MaintenanceSchedule(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('EM_ANDAMENTO', 'Em Andamento'),
        ('CONCLUIDO', 'Concluído'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    veiculo = models.ForeignKey(Veiculo, on_delete=models.CASCADE, related_name='schedules')
    data_paralizacao = models.DateTimeField()
    data_previsao_liberacao = models.DateTimeField()
    descricao = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    criado_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name='schedules_created')
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Agendamento de Manutenção"
        verbose_name_plural = "Agendamentos de Manutenção"

    def __str__(self):
        return f"Manutenção {self.veiculo.placa} - {self.data_paralizacao.strftime('%d/%m/%y')}"

class AlertWhatsApp(models.Model):
    nome = models.CharField(max_length=100)
    ddd = models.CharField(max_length=2)
    numero = models.CharField(max_length=9)
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Alerta de WhatsApp"
        verbose_name_plural = "Alertas de WhatsApp"

    def __str__(self):
        return f"{self.nome} ({self.ddd}{self.numero})"

    @property
    def numero_completo(self):
        return f"55{self.ddd}{self.numero}"

class MaintenanceStatusLog(models.Model):
    schedule = models.ForeignKey(MaintenanceSchedule, on_delete=models.CASCADE, related_name='logs')
    old_status = models.CharField(max_length=20, choices=MaintenanceSchedule.STATUS_CHOICES)
    new_status = models.CharField(max_length=20, choices=MaintenanceSchedule.STATUS_CHOICES)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Histórico de Manutenção"
        verbose_name_plural = "Históricos de Manutenção"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_new_status_display()} em {self.created_at.strftime('%d/%m/%y %H:%M')}"
