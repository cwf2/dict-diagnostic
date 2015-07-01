# -*- coding: utf-8

import re
import unicodedata

def beta_to_uni(beta):
	code = [		
		(r'\)', "\u0313"),
		(r'\(', "\u0314"),
		(r'\/', "\u0301"),
		(r'\=', "\u0342"),
		(r'\\', "\u0300"),
		(r'\+', "\u0308"),
		(r'\|', "\u0345"),
	
		(r'\*a', 'Α'),	(r'a', 'α'),
		(r'\*b', 'Β'),	(r'b', 'β'),
		(r'\*g', 'Γ'),	(r'g', 'γ'),
		(r'\*d', 'Δ'),	(r'd', 'δ'),
		(r'\*e', 'Ε'),	(r'e', 'ε'),
		(r'\*z', 'Ζ'),	(r'z', 'ζ'),
		(r'\*h', 'Η'),	(r'h', 'η'),
		(r'\*q', 'Θ'),	(r'q', 'θ'),
		(r'\*i', 'Ι'),	(r'i', 'ι'),
		(r'\*k', 'Κ'),	(r'k', 'κ'),
		(r'\*l', 'Λ'),	(r'l', 'λ'),
		(r'\*m', 'Μ'),	(r'm', 'μ'),
		(r'\*n', 'Ν'),	(r'n', 'ν'),
		(r'\*c', 'Ξ'),	(r'c', 'ξ'),
		(r'\*o', 'Ο'),	(r'o', 'ο'),
		(r'\*p', 'Π'),	(r'p', 'π'),
		(r'\*r', 'Ρ'),	(r'r', 'ρ'),
						(r's\b', 'ς'),
		(r'\*s', 'Σ'),	(r's', 'σ'),
		(r'\*t', 'Τ'),	(r't', 'τ'),
		(r'\*u', 'Υ'),	(r'u', 'υ'),
		(r'\*f', 'Φ'),	(r'f', 'φ'),
		(r'\*x', 'Χ'),	(r'x', 'χ'),
		(r'\*y', 'Ψ'),	(r'y', 'ψ'),
		(r'\*w', 'Ω'),	(r'w', 'ω')
	]
	
	caps_adj = re.compile(r'(\*)([^a-z ]+)')
	
	beta = caps_adj.sub(r'\2\1', beta)
	
	for t in code:
		pat, sub = t
		
		pat = re.compile(pat)
		
		beta = pat.sub(sub, beta)
	
	return beta


def standardize(lang, lemma):
	'''Standardize orthography of greek and latin words'''

	if lang == 'la':
		lemma = lemma.replace('j', 'i')
		lemma = lemma.replace('v', 'u')

	if lang == 'grc':
		lemma = lemma.replace('\\', '/')
		lemma = beta_to_uni(lemma)

	lemma = unicodedata.normalize('NFKD', lemma)
	lemma = lemma.lower()	

	return(lemma)
