from django.db import models
from django.db.models import Sum


# prova modifica seconda volta

# Create your models here.

# tipi generici per DDL

CARATTERISTICA = "CA"
STATISTICA = "ST"
ELEMENTO = "EL"
AURA = "AU"

punteggi_tipo = [
	(CARATTERISTICA, 'Caratteristica'),
	(STATISTICA, 'Statistica'),
	(ELEMENTO, 'Elemento'),
	(AURA, 'Aura',)
	]

TIER_1 = "T1"
TIER_2 = "T2"
TIER_3 = "T3"
TIER_4 = "T4"

tabelle_tipo = [
	(TIER_1, 'Tier 1'),
	(TIER_2, 'Tier 2'),
	(TIER_3, 'Tier 3'),
	(TIER_4, 'Tier 4'),
	]


# Classi astratte

class A_modello(models.Model):
	id = models.AutoField("Codice Identificativo", primary_key = True, )
	class Meta:
		abstract = True
		


#definizioni classi

class Tabella(A_modello):
	nome = models.CharField("Nome", max_length = 90, )
	descrizione = models.TextField("descrizione", null=True, blank=True, )

	class Meta:
		verbose_name = "Tabella"
		verbose_name_plural = "Tabelle"

	def __str__(self):
		return self.nome

class Tier(Tabella):
	tipo = models.CharField('Tier', choices=tabelle_tipo, max_length=2)	

	class Meta:
		verbose_name = "Tier"
		verbose_name_plural = "Tiers"

class Punteggio(Tabella):
	sigla = models.CharField('Sigla', max_length=3, unique=True, )
	tipo = models.CharField('Tipo di punteggio', choices=punteggi_tipo, max_length=2)
	caratteristica = models.ForeignKey(
		"Punteggio",
		on_delete=models.CASCADE, 
		limit_choices_to={'tipo' : CARATTERISTICA},
		null=True, blank=True,
		verbose_name = "Carattesitica relativa",
		related_name = "punteggi_caratteristica",
		)
	
	class Meta:
		verbose_name = "Punteggio"
		verbose_name_plural = "Punteggi"
		ordering =['tipo', 'nome']

	def __str__(self):
		result = "{tipo} - {nome}"
		return result.format(nome=self.nome, tipo = self.tipo)

class Abilita(A_modello):
	nome = models.CharField("Nome dell'abilità", max_length = 90, )
	descrizione = models.TextField('Descrizione', null=True, blank=True,)
	caratteristica = models.ForeignKey(
		Punteggio,  
		on_delete=models.CASCADE,
		verbose_name="Caratteristica", 
		limit_choices_to={'tipo' : CARATTERISTICA}
		)
	tiers = models.ManyToManyField(
		Tier,
		related_name = "abilita",
		through = "abilita_tier",
		help_text = "Tiers in cui è presente l'abilità",
		)
	requisiti = models.ManyToManyField(
		Punteggio,
		related_name = "abilita_req",
		through = "abilita_requisito",
		help_text = "Caratteristiche requisito di sblocco",
		limit_choices_to={'tipo' : CARATTERISTICA}
		)
	tabelle_sbloccate = models.ManyToManyField(
		Tabella,
		related_name = "abilita_sbloccante",
		through = "abilita_sbloccata",
		help_text = "Tabelle sbloccate dall'abilità",
		)
	punteggio_acquisito = models.ManyToManyField(
		Punteggio,
		related_name = "abilita_acquisizione",
		through = "abilita_punteggio",
		help_text = "Caratteristiche requisito di sblocco",
		)
	# prerequisiti = models.ManyToManyField(
	# 	"Abilita",
	# 	related_name = "abilitati",
	# 	through = "abilita_prerequisito",
	# 	help_text = "Abilità che fungono da prerequisito",
	# )
 
 
	class Meta:
		verbose_name = "Abilità"
		verbose_name_plural = "Abilità"

	def __str__(self):
		return self.nome

class Spell(A_modello):
	nome = models.CharField("Nome dell'abilità attivata", max_length=90, )
	descrizione = models.TextField("Descrizione", null=True, blank=True, )
	mattoni = models.ManyToManyField(
		"Mattone",
		related_name = "spells",
		through = "spell_mattone",
		help_text = "Mattoni requisito dell'abilità attivata",
		)
	#livello = elementi.all().count()
#	def livello(self):
#		return self.mattoni.all().aggregate(Sum())

	class Meta:
		verbose_name = "Abilità attivata"
		verbose_name_plural = "Abilità attivate"

	def __str__(self):
		return self.nome
	
class Mattone(A_modello):
	nome = models.CharField("Nome del mattone", max_length = 40)
	descrizione = models.TextField("Descrizione del mattone", null=True, blank=True,)
	elemento = models.ForeignKey(
		Punteggio, 
		on_delete=models.CASCADE, 
		limit_choices_to={'tipo' : ELEMENTO}, 
		related_name = "elemento_mattone",
		)
	aura = models.ForeignKey(
		Punteggio, 
		on_delete=models.CASCADE, 
		limit_choices_to={'tipo' : AURA}, 
		related_name = "aura_mattone",
		)
	class Meta:
		verbose_name = "Mattone"
		verbose_name_plural = "Mattoni"

	def __str__(self):
		result = "{nome} ({aura} - {elemento})"
		
		return result.format(nome=self.nome, aura=self.aura.sigla, elemento=self.elemento.sigla)

		

# Classi Through

class abilita_tier(A_modello):
	abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE, )
	tabella = models.ForeignKey(Tier, on_delete=models.CASCADE, )
	costo = models.IntegerField("Costo dell'abilità", default=10, )
	ordine = models.IntegerField("Ordine in tabella", default=10, )
	
	class Meta:
		verbose_name = "Abilità - Tier"
		verbose_name_plural = "Abilità - Tiers"
		ordering = ["ordine", "abilita__nome", ]

	def __str__(self):
		testo = "{abilita} - {tabella} ({costo})"
		return testo.format(abilita=self.abilita.nome, tabella=self.tabella.nome, costo=self.costo)

class abilita_prerequisito(A_modello):
	abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE, related_name="abilita_prerequisiti", )
	prerequisito = models.ForeignKey(Abilita, on_delete=models.CASCADE, related_name="abilita_abilitati", )

	class Meta:
		verbose_name = "Abilità - Prerequisito"
		verbose_name_plural = "Abilità - Prerequisiti"

	def __str__(self):
		testo = "{abilita} necessita {prerequisito}"
		return testo.format(abilita=self.abilita.nome, prerequisito=self.prerequisito.nome)

 
class abilita_requisito(A_modello):
	abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE, )
	requisito = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo' : CARATTERISTICA})
	valore = models.IntegerField("Punteggio della caratteristica", default=1, )
	
	class Meta:
		verbose_name = "Abilità - Requisito"
		verbose_name_plural = "Abilità - Requisiti"

	def __str__(self):
		testo = "{abilita} necessita {requisito}: {valore}"
		return testo.format(abilita=self.abilita.nome, requisito=self.requisito.nome, valore=self.valore)

class abilita_sbloccata(A_modello):
	abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE, )
	sbloccata = models.ForeignKey(Tabella, on_delete=models.CASCADE, )

	class Meta:
		verbose_name = "Abilità - Tabella sbloccata"
		verbose_name_plural = "Abilità - Tabelle sbloccate"

	def __str__(self):
		testo = "{abilita} sblocca {sbloccata}"
		return testo.format(abilita=self.abilita.nome, sbloccata=self.sbloccata.nome)

	
class abilita_punteggio(A_modello):
	abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE, )
	punteggio = models.ForeignKey(Punteggio, on_delete=models.CASCADE, )
	valore = models.IntegerField("Punteggio della caratteristica", default=1, )

	class Meta:
		verbose_name = "Abilità - Punteggio assegnato"
		verbose_name_plural = "Abilità - Punteggi assegnati"

	def __str__(self):
		testo = "{abilita} -> {punteggio} ({valore})"
		return testo.format(abilita=self.abilita.nome, punteggio=self.punteggio.nome, valore=self.valore)
	
class spell_elemento(A_modello):
	spell = models.ForeignKey(Spell, on_delete=models.CASCADE, )	
	elemento = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo' : ELEMENTO}, )

	class Meta:
		verbose_name = "Spell - Elemento necessario"
		verbose_name_plural = "Spell - Elementi necessari"

	def __str__(self):
		testo = "{spell} necessita {elemento}"
		return testo.format(spell=self.spell.nome, elemento=self.elemento.nome)
	
class spell_mattone(A_modello):
	spell = models.ForeignKey(Spell, on_delete=models.CASCADE, )	
	mattone = models.ForeignKey(Mattone, on_delete=models.CASCADE, )
	valore = models.IntegerField("Ripetizioni del mattone", default=1, )

	class Meta:
		verbose_name = "Abilità attivata - Mattone necessario"
		verbose_name_plural = "Abilità attivate - Mattoni necessari"

	def __str__(self):
		testo = "{spell} necessita {mattone} {liv}"
		return testo.format(spell=self.spell.nome, mattone=self.mattone.nome, liv=self.valore)


