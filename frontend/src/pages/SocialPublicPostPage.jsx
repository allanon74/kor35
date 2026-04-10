import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { socialGetPublicPostBySlug } from '../api';

export default function SocialPublicPostPage() {
  const { slug } = useParams();
  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await socialGetPublicPostBySlug(slug);
        if (mounted) setPost(data);
      } catch (e) {
        if (mounted) setError('Post non trovato o non pubblico.');
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => {
      mounted = false;
    };
  }, [slug]);

  if (loading) return <div className="p-8 text-center text-gray-500">Caricamento post...</div>;
  if (error) return <div className="p-8 text-center text-red-500">{error}</div>;
  if (!post) return null;

  return (
    <div className="max-w-3xl mx-auto p-4 md:p-8">
      <div className="bg-white rounded-xl shadow border border-gray-200 p-5 space-y-4">
        <h1 className="text-2xl md:text-3xl font-bold text-gray-900">{post.titolo}</h1>
        <p className="text-sm text-gray-500">
          Pubblicato da <span className="font-semibold">{post.autore_nome}</span> ·{' '}
          {new Date(post.created_at).toLocaleString('it-IT')}
        </p>

        {post.testo && <p className="text-gray-800 whitespace-pre-wrap">{post.testo}</p>}
        {post.immagine && <img src={post.immagine} alt={post.titolo} className="w-full rounded-lg border border-gray-200" />}
        {post.video && <video src={post.video} controls className="w-full rounded-lg border border-gray-200" />}

        <div className="text-sm text-gray-600 border-t border-gray-200 pt-3">
          Like: <span className="font-semibold">{post.likes_count || 0}</span> · Commenti:{' '}
          <span className="font-semibold">{post.comments_count || 0}</span>
        </div>
      </div>

      <div className="mt-4 text-center">
        <Link to="/app/social" className="text-indigo-600 hover:text-indigo-500 font-semibold">
          Apri InstaFame
        </Link>
      </div>
    </div>
  );
}
