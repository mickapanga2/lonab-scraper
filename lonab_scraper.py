#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de scraping LONAB pour n8n sur Render.com
Optimisé pour l'environnement cloud
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import sys
import os

def scrape_lonab():
    """Scraper LONAB optimisé pour Render"""
    url = "http://www.lonab.bf"
    
    result = {
        "extraction_date": datetime.now().isoformat(),
        "source_url": url,
        "selector": "#block-resultats > div",
        "success": False,
        "error": None,
        "items": [],
        "raw_count": 0,
        "environment": "render.com"
    }
    
    try:
        # Headers pour éviter les blocages
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Télécharger avec timeout adapté au cloud
        response = requests.get(url, timeout=15, headers=headers)
        response.raise_for_status()
        
        # Parser le HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Debug: afficher une partie du HTML
        print(f"HTML reçu: {len(response.text)} caractères", file=sys.stderr)
        
        # Trouver les éléments
        elements = soup.select("#block-resultats > div")
        result["raw_count"] = len(elements)
        
        # Si pas d'éléments, essayer des sélecteurs alternatifs
        if not elements:
            alternative_selectors = [
                ".block-resultats div",
                "[id*='resultat'] div",
                ".results div",
                ".tirage div"
            ]
            
            for alt_selector in alternative_selectors:
                elements = soup.select(alt_selector)
                if elements:
                    result["selector"] = alt_selector
                    result["raw_count"] = len(elements)
                    break
        
        if not elements:
            # Chercher tout div contenant des mots-clés
            all_divs = soup.find_all('div')
            keywords = ['tirage', 'resultat', 'gagnant', 'numero', 'fcfa']
            
            for div in all_divs:
                text = div.get_text().lower()
                if any(keyword in text for keyword in keywords) and len(text.strip()) > 10:
                    elements.append(div)
            
            result["raw_count"] = len(elements)
            result["selector"] = "fallback_keyword_search"
        
        if not elements:
            result["error"] = "Aucun élément trouvé avec tous les sélecteurs"
            return result
        
        # Traiter chaque résultat
        for i, element in enumerate(elements[:10], 1):  # Limiter à 10 pour éviter les timeouts
            content = element.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            
            if len('\n'.join(lines)) < 10:  # Ignorer les éléments trop courts
                continue
            
            element_data = {
                "item_number": i,
                "text_content": '\n'.join(lines),
                "text_lines": lines,
                "html_classes": element.get('class', []),
                "extraction_timestamp": datetime.now().isoformat(),
                "content_length": len(content)
            }
            
            # Détecter les patterns avec regex robuste
            import re
            
            # Numéros de tirage (formats variés)
            number_patterns = [
                r'\b\d{2}-\d{2}-\d{2}(?:-\d{2})*\b',  # XX-XX-XX
                r'\b\d{2}\s+\d{2}\s+\d{2}(?:\s+\d{2})*\b',  # XX XX XX
                r'\b\d{1,2}/\d{1,2}/\d{2,4}\b'  # Dates
            ]
            
            detected_numbers = []
            for pattern in number_patterns:
                matches = re.findall(pattern, content)
                detected_numbers.extend(matches)
            
            if detected_numbers:
                element_data["detected_numbers"] = list(set(detected_numbers))
            
            # Montants FCFA (patterns variés)
            money_patterns = [
                r'([\d\s,.]+)\s*(?:FCFA|CFA|F\s*CFA)',
                r'(\d{1,3}(?:[,.\s]\d{3})*)\s*(?:FCFA|CFA)',
                r'([\d,.\s]+)\s*(?:francs?|F)'
            ]
            
            detected_amounts = []
            for pattern in money_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                detected_amounts.extend([match.strip() if isinstance(match, str) else match[0].strip() for match in matches])
            
            if detected_amounts:
                element_data["detected_amounts"] = list(set(detected_amounts))
            
            # Dates
            dates = re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', content)
            if dates:
                element_data["detected_dates"] = dates
            
            # Classification du contenu
            content_lower = content.lower()
            if any(word in content_lower for word in ['tirage', 'resultat', 'gagnant']):
                element_data["content_type"] = "resultat"
            elif any(word in content_lower for word in ['annonce', 'info', 'prochaine']):
                element_data["content_type"] = "annonce"
            else:
                element_data["content_type"] = "unknown"
            
            result["items"].append(element_data)
        
        result["success"] = True
        print(f"LONAB SUCCESS: {len(result['items'])} éléments extraits", file=sys.stderr)
        
    except requests.exceptions.Timeout:
        result["error"] = "Timeout: le site LONAB met trop de temps à répondre"
    except requests.exceptions.ConnectionError:
        result["error"] = "Erreur de connexion au site LONAB"
    except requests.exceptions.RequestException as e:
        result["error"] = f"Erreur réseau: {str(e)}"
    except Exception as e:
        result["error"] = f"Erreur: {str(e)}"
        print(f"LONAB ERROR: {e}", file=sys.stderr)
    
    return result

def main():
    """Point d'entrée optimisé pour Render"""
    try:
        # Afficher l'environnement
        print(f"Environment: Render.com", file=sys.stderr)
        print(f"Python version: {sys.version}", file=sys.stderr)
        
        # Exécuter le scraping
        result = scrape_lonab()
        
        # Sortie JSON compacte pour réduire la bande passante
        print(json.dumps(result, ensure_ascii=False, separators=(',', ':')))
        
        sys.exit(0 if result["success"] else 1)
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": f"Erreur critique: {str(e)}",
            "items": [],
            "environment": "render.com"
        }
        print(json.dumps(error_result, ensure_ascii=False))
        sys.exit(1)

if __name__ == "__main__":
    main()
