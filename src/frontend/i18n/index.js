import { useEffect, useState } from 'react';
import translations from './translations.json'; // Import your JSON translation file

const defaultLanguage = 'en';

const useLanguage = () => {
  const [language, setLanguage] = useState(defaultLanguage);

  useEffect(() => {
    // Load language from local storage if available
    const storedLanguage = localStorage.getItem('language');
    if (storedLanguage) {
      setLanguage(storedLanguage);
    }
  }, []);

  const switchLanguage = async (languageCode) => {
    const supportedLanguages = Object.keys(translations);
    if (!supportedLanguages.includes(languageCode)) {
      console.error(`Invalid language code: ${languageCode}`);
      alert('Invalid language code'); // or a more graceful error display
      return;
    }

    try {
      const response = await fetch('/language/switch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ language_code: languageCode }),
      });

      if (response.ok) {
        localStorage.setItem('language', languageCode);
        setLanguage(languageCode);
      } else {
        console.error('Failed to switch language:', response.status);
        alert('Failed to switch language'); // Or a better error message
      }
    } catch (error) {
      console.error('Error switching language:', error);
      alert('Error switching language');
    }
  };

  const getTranslation = (key) => {
    const currentTranslation = translations[language];
    return currentTranslation && currentTranslation[key] ? currentTranslation[key] : (translations[defaultLanguage]?.[key] || key); // Fallback to default or key itself
  };

  return { language, switchLanguage, getTranslation };
};

export default useLanguage;